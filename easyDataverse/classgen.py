import forge
import types
import re

from enum import Enum
from pydantic import AnyHttpUrl, EmailStr, create_model, Field
from pydantic.fields import FieldInfo
from typing import List, Tuple, Union, Type, Optional, Dict, Callable

from easyDataverse.base import DataverseBase

TYPE_MAPPING = {
    "text": str,
    "url": AnyHttpUrl,
    "float": float,
    "integer": int,
    "int": int,
    "textbox": str,
    "date": str,
    "email": EmailStr,
}


def create_dataverse_class(
    name: str,
    primitives: List[Dict],
    compounds: Optional[List] = None,
    common_part="",
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
        [camel_to_snake(field["name"]) for field in primitives]
        + [camel_to_snake(field["name"]) for field in compounds]
    )

    # Get all primitive attributes
    attributes = {
        process_name(field["name"], common_part): (
            get_field_type(field),
            prepare_field_meta(field),
        )
        for field in primitives
    }

    # Get all compounds and collect add function
    add_functions = {}
    attributes.update(
        {
            process_name(compound["name"], common_part): create_compound(
                compound, add_functions, common_part
            )
            for compound in compounds
        }
    )

    # Create the class and add utilities
    dv_class = create_model(
        cls_name,
        __base__=(DataverseBase,),
        **attributes,
    )

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
        common_part (str, optional): Common part of the compound name. Defaults to "".

    Returns:
        Tuple[Callable, FieldInfo]: Class as a type and Field meta for PyDantic
    """

    # Get all the names
    attribute_name = process_name(
        compound["name"],
        common_part,
    )

    sub_cls = create_dataverse_class(
        compound["title"],
        compound["childFields"].values(),
    )

    if compound["multiple"] is True:
        dtype = list_type(sub_cls)
    else:
        dtype = optional_type(sub_cls)

    field_meta = prepare_field_meta(compound)

    if compound["multiple"] is False:
        # Set non-multiple compounds directly as default
        field_meta.default = None
        field_meta.default_factory = sub_cls

    # Create add function
    fun_name = f"add_{attribute_name}"
    add_functions[fun_name] = generate_add_function(sub_cls, attribute_name, fun_name)

    return (dtype, field_meta)


def get_field_type(field: Dict) -> Type:
    """Retrieves the type hint of a field

    Args:
        field (Dict): The field dictionary containing information about the field

    Returns:
        Type: The type hint of the field

    """
    if field["isControlledVocabulary"]:
        dtype = Enum(
            field["name"],
            {
                spaced_to_snake(value).upper(): value
                for value in field["controlledVocabularyValues"]
            },
        )
    else:
        dtype = TYPE_MAPPING[field["type"].lower()]

    if field["multiple"]:
        return list_type(dtype)
    else:
        return optional_type(dtype)


def prepare_field_meta(field: Dict) -> FieldInfo:
    """
    Extracts metadata from the field definition to compose a PyDantic Field instance.

    Args:
        field (Dict): The field definition.

    Returns:
        FieldInfo: The PyDantic Field instance.
    """

    is_multiple = field["multiple"]

    if field["type"].lower() == "none":
        type_class = "compound"
    elif field["isControlledVocabulary"]:
        type_class = "controlledVocabulary"
    else:
        type_class = "primitive"

    field_parameters = {
        "alias": field["name"],
        "description": field["description"],
    }

    json_schema_extra = {
        "multiple": is_multiple,
        "typeClass": type_class,
        "typeName": field["name"],
    }

    if is_multiple:
        field_parameters["default_factory"] = list
    else:
        field_parameters["default"] = None

    return Field(
        **field_parameters,
        json_schema_extra=json_schema_extra,
    )


def generate_add_function(subclass, attribute, name):
    """Generates an add function for a subclass.

    Args:
        subclass (class): The subclass to be added.
        attribute (str): The attribute name to append the subclass instance to.
        name (str): The name of the generated add function.

    Returns:
        function: The generated add function.
    """

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
    """
    Forges a signature for an add function

    Args:
        subclass: The subclass for which the signature is being forged

    Returns:
        signature: The forged signature as a list of keyword arguments
    """
    signature = []
    for name, dtype in subclass.__annotations__.items():
        sig_params = {"name": name, "type": dtype, "interface_name": name}

        default = subclass.model_fields[name].default

        if default is None:
            sig_params["default"] = None

        signature.append(forge.kwarg(**sig_params))

    return signature


def clean_name(name):
    """
    Removes anything that is not a valid variable name.

    Parameters:
        name (str): The name to be cleaned.

    Returns:
        str: The cleaned name.
    """
    return re.sub(r"[^\w\s_]", " ", name).strip()


def camel_to_snake(name):
    """
    Converts a camel case string to snake case.

    Args:
        name (str): The camel case string to be converted.

    Returns:
        str: The snake case representation of the input string.
    """

    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", clean_name(name))
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def spaced_to_snake(name: str) -> str:
    """Turns names that contain a space into snake case

    Args:
        name (str): The name to be converted to snake case.

    Returns:
        str: The name converted to snake case.

    """
    name = clean_name(name).strip("_").strip()

    if name == "":
        raise ValueError(f"Class name cannot be empty. Got '{name}'")

    return "_".join([word.lower() for word in name.replace("-", " ").split(" ")])


def construct_class_name(name: str) -> str:
    """Converts a display name to a class name.

    Args:
        name (str): The display name to be converted.

    Returns:
        str: The converted class name.

    Raises:
        ValueError: If the name is empty.

    """
    name = spaced_to_snake(name)

    if name == "":
        raise ValueError(f"Class name cannot be empty. Got '{name}'")

    return "".join([part.capitalize() for part in name.split("_")])


def list_type(dtype: Type):
    """Encapsulates given types within a List typing

    Args:
        dtype (Type): The type to be encapsulated

    Returns:
        List[dtype]: The encapsulated type as a List

    """
    return List[dtype]


def optional_type(dtype: Type):
    """Encapsulates given types within an Optional typing

    Args:
        dtype (Type): The type to be encapsulated

    Returns:
        Optional[Type]: The encapsulated type wrapped in Optional

    """
    return Optional[dtype]


def union_type(dtypes: Tuple):
    """Encapsulates given types within a Union typing

    Args:
        dtypes (Tuple): A tuple of types to be encapsulated within a Union typing

    Raises:
        ValueError: If only a single type is provided

    Returns:
        Union: A Union typing encapsulating the given types
    """

    if not isinstance(dtypes, tuple):
        raise TypeError(f"Expected a tuple of types, got {type(dtypes)}")

    if len(dtypes) < 2:
        raise ValueError("Union type requires more than a single type")

    return Union[dtypes]  # type: ignore


def remove_child_fields_from_global(fields: Dict) -> Dict:
    """
    Removes fields that belong to a compound from the global scope.

    Args:
        fields (Dict): A dictionary containing the fields.

    Returns:
        Dict: The updated dictionary with the removed fields.
    """

    compounds = list(filter(lambda field: "childFields" in field, fields.values()))
    for compound in compounds:
        for child_name in compound["childFields"].keys():
            if child_name in fields:
                fields.pop(child_name)

    return fields


def process_name(attr_name, common_part):
    """
    Process the attribute name by converting it from camel case to snake case and removing the common part.

    Args:
        attr_name (str): The attribute name to be processed.
        common_part (str): The common part to be removed from the attribute name.

    Returns:
        str: The processed attribute name.
    """
    return camel_to_snake(attr_name).replace(common_part, "", 1).replace(" ", "")


def find_common_name_part(names: List[str]):
    """
    Finds a common name part to remove this across primitives and compounds

    Args:
        names (List[str]): A list of names to find the common part from.

    Returns:
        str: The common name part found.

    Raises:
        None

    Examples:
        >>> names = ["apple", "banana", "apricot"]
        >>> find_common_name_part(names)
        'a_'
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
