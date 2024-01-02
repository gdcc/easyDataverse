import grequests
import forge
import types
import re
import requests

from enum import Enum
from functools import cache
from datetime import date
from urllib.parse import urljoin, urlparse
from dotted_dict import DottedDict
from pydantic import create_model, AnyHttpUrl, EmailStr, Field
from pydantic.fields import FieldInfo
from typing import List, Tuple, Union, Type, Optional, Dict, Callable

from easyDataverse.base import DataverseBase

REQUIRED_FIELDS = []
TYPE_MAPPING = {
    "text": str,
    "url": AnyHttpUrl,
    "float": float,
    "integer": int,
    "int": int,
    "textbox": str,
    "date": date,
    "email": EmailStr,
}


@cache
def fetch_metadatablocks(url: AnyHttpUrl) -> Dict:
    """Fetches all metadatablocks from a given URL"""

    url = urlparse(str(url))
    all_blocks_url = urljoin(url.geturl(), "api/metadatablocks")

    response = requests.get(all_blocks_url)

    if not response.ok:
        raise requests.HTTPError(
            f"URL '{url.geturl()}' is not a valid Dataverse installation. Couldnt find info on metadata blocks."
        )

    all_blocks = response.json()["data"]
    names = [block["name"] for block in all_blocks]
    fetched_blocks = grequests.map(_prepare_block_requests(url, names))

    return {
        name: DottedDict(block.json()) for name, block in zip(names, fetched_blocks)
    }


def _prepare_block_requests(url: AnyHttpUrl, names: List[str]):
    """Create a generator that is used to parallel fetch metadatablocks"""
    return (
        grequests.get(urljoin(url.geturl(), f"api/metadatablocks/{name}"))
        for name in names
    )


def fetch_single_metadatablock(url: AnyHttpUrl, name: str):
    """Fetches a single metadatablock from an installation"""

    single_block_url = urljoin(url.geturl(), f"api/metadatablocks/{name}")

    response = requests.get(single_block_url)

    if not response.ok:
        raise requests.HTTPError(
            f"Metadatablock '{name}' is not present at Dataverse installation '{url.geturl()}'. You may need to check with your administrator, something seems to be wrong here.."
        )

    return DottedDict(response.json())


def create_dataverse_class(
    name: str, primitives: List[Dict], compounds: List = None, common_part=""
) -> Callable:
    """Parses the parameters given by a dataverse metadatablock definition
    and dynamically creates a class that can be used to report data
    to a dataset.

    Args:
        name (str): Name of the metadatablock/field
        primitives (List[Dict]): List of primitive fields to parse.
        compounds (List, optional): List of compound fields to parse. Defaults to None.

    Returns:
        Callable: DataverseBase class that can be used within the Dataset/DataverseBase class
    """

    if compounds is None:
        compounds = []

    cls_name = construct_class_name(name)

    # Cosmetics :-P
    common_part = find_common_name_part(
        [camel_to_snake(field.name) for field in primitives]
        + [camel_to_snake(field.name) for field in compounds]
    )

    # Get all primitive attributes
    attributes = {
        process_name(field.name, common_part): (
            get_field_type(field),
            prepare_field_meta(field),
        )
        for field in primitives
    }

    # Get all compounds and collect add function
    add_functions = {}
    attributes.update(
        {
            process_name(compound.name, common_part): create_compound(
                compound, add_functions, common_part
            )
            for compound in compounds
        }
    )

    # Create the class and add utilities
    dv_class = create_model(cls_name, __base__=(DataverseBase,), **attributes)

    for name, fun in add_functions.items():
        setattr(dv_class, name, fun)

    return dv_class


def create_compound(
    compound: Dict,
    add_functions: Dict,
    common_part: str = "",
) -> Tuple[Callable, FieldInfo]:
    """Takes a compound definition, creates a corresponding data type and an add_function

    Args:
        compound (Dict): Dictionary containing the compound configuration
        add_functions (Dict): Add function registry which will be added to the parent class.

    Returns:
        Tuple[Callable, FieldInfo]: Class as a type and Field meta for PyDantic
    """

    # Get all the names
    attribute_name = process_name(compound.name, common_part)
    sub_cls = create_dataverse_class(compound.title, compound.childFields.values())
    dtype = get_field_type(compound, sub_cls)
    field_meta = prepare_field_meta(compound)

    if compound.multiple is False:
        # Set non-multiple compounds directly as default
        field_meta.default = None
        field_meta.default_factory = sub_cls

    # Create add function
    fun_name = f"add_{attribute_name}"
    add_functions[fun_name] = generate_add_function(sub_cls, attribute_name, fun_name)

    return (dtype, field_meta)


def get_field_type(field: Dict, compound_class=None) -> Type:
    """Retrieves the type hint of a field"""

    if field.isControlledVocabulary:
        dtype = Enum(
            field.name,
            {
                spaced_to_snake(value).upper(): value
                for value in field.controlledVocabularyValues
            },
        )
    elif compound_class is not None:
        dtype = compound_class
    else:
        dtype = TYPE_MAPPING[field.type.lower()]

    if field.multiple:
        return list_type(dtype)
    else:
        return optional_type(dtype)


def prepare_field_meta(field: Dict) -> FieldInfo:
    """Extracts metadata from the field definition to compose a PyDantic Field instance"""

    is_multiple = field["multiple"]
    is_required = field["name"] in REQUIRED_FIELDS

    if field.type.lower() == "none":
        type_class = "compound"
    elif field.isControlledVocabulary:
        type_class = "controlledVocabulary"
    else:
        type_class = "primitive"

    field_parameters = {
        "multiple": is_multiple,
        "typeClass": type_class,
        "typeName": field.name,
        "description": field.description,
    }

    if is_multiple:
        field_parameters["default_factory"] = list
    elif is_required:
        field_parameters["default"] = ...
    else:
        field_parameters["default"] = None

    return Field(**field_parameters)


def generate_add_function(subclass, attribute, name):
    """Generates an add functon for a subclass"""

    def add_fun_template(self, **kwargs):
        getattr(self, attribute).append(subclass(**kwargs))

    signature = create_function_signature(subclass)
    new_func = forge.sign(forge.self, *signature)(
        types.FunctionType(
            add_fun_template.__code__,
            add_fun_template.__globals__,
            name,
            add_fun_template.__defaults__,
            add_fun_template.__closure__,
        )
    )

    new_func.__annotations__ = dict(subclass.__annotations__)
    new_func.__doc__ = str(forge.repr_callable(new_func))

    return new_func


def create_function_signature(subclass) -> List:
    """Forges a signature for an add function"""

    signature = []
    for name, dtype in subclass.__annotations__.items():
        sig_params = {"name": name, "type": dtype, "interface_name": name}

        default = subclass.__fields__[name].default

        if default is None:
            sig_params["default"] = None

        signature.append(forge.kwarg(**sig_params))

    return signature


def clean_name(name):
    """Removes anything that is not a valid variable name"""
    return re.sub(r"-|\?|\(|\)|\[|\]|\.", "", name)


def camel_to_snake(name):
    """Turns camel case to snake case"""

    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", clean_name(name))
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def spaced_to_snake(name) -> str:
    """Turns names that contain a space into snake case"""

    name = clean_name(name).replace(r"/", " ")

    return "_".join([word.lower() for word in name.replace("-", " ").split(" ")])


def construct_class_name(name) -> str:
    """Converts a display name to a class name"""
    name = spaced_to_snake(name)

    return "".join([part.capitalize() for part in name.split("_")])


def list_type(dtype: Type):
    """Encapsulates given types within a List typing"""
    return List[dtype]


def optional_type(dtype: Type):
    """Encapsulates given types within an Optional typing"""
    return Optional[dtype]


def union_type(dtypes: Tuple):
    """Encapsulates given types within a Union typing"""

    if len(dtypes) == 1:
        raise ValueError(f"Union type requires more than a single type")

    return Union[dtypes]


def remove_child_fields_from_global(fields: Dict) -> Dict:
    """Removes fields that belong to a compound from the global scope"""

    compounds = list(filter(lambda field: "childFields" in field, fields.values()))
    for compound in compounds:
        for child_name in compound.childFields.keys():
            if child_name in fields:
                fields.pop(child_name)

    return fields


def process_name(attr_name, common_part):
    return camel_to_snake(attr_name).replace(common_part, "", 1)


def find_common_name_part(names: List[str]):
    """Finds a common name part to remove this across primitives and compounds

    Looks better!!!
    """

    if len(names) <= 1:
        return ""

    diff = False
    common_start = []

    while diff is False:
        try:
            current_char_set = {name.split("_")[len(common_start)] for name in names}
        except IndexError:
            return "_".join(common_start) + "_"

        if len(current_char_set) == 1:
            common_start += list(current_char_set)
        else:
            diff = True

    if len(common_start) == 0:
        return ""

    return "_".join(common_start) + "_"
