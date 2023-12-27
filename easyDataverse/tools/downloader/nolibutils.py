import copy
import json
import forge
import re
import requests

from pyDataverse.api import NativeApi
from pydantic import Field, create_model
from typing import Optional, List, Dict, List

from easyDataverse.core.base import DataverseBase


class Types:
    """Enumeration used to infer type annotations for PyDantic"""

    STR = str
    FLOAT = float
    INT = int

    LIST_STR = List[str]
    LIST_FLOAT = List[float]
    LIST_INT = List[int]

    OPTIONAL_STR = Optional[str]
    OPTIONAL_FLOAT = Optional[float]
    OPTIONAL_INT = Optional[int]

    @classmethod
    def get_mixed_type(
        cls, dtype: str, multiple: bool = False, required: bool = False, pre: str = ""
    ):
        STRING_TYPES = ["text", "textbox", "url", "date"]
        FLOAT_TYPES = ["float"]
        INTEGER_TYPES = ["integer"]

        if not required:
            pre = "OPTIONAL_"
        if multiple:
            pre = "LIST_"

        if dtype.lower() in STRING_TYPES:
            return cls.__dict__[f"{pre}STR"]
        elif dtype.lower() in FLOAT_TYPES:
            return cls.__dict__[f"{pre}FLOAT"]
        elif dtype.lower() in INTEGER_TYPES:
            return cls.__dict__[f"{pre}INT"]
        else:
            return cls.__dict__[f"{pre}STR"]


# ! STEP 1 UTILS: Fetching of the raw Dataverse JSON data
def fetch_dataset(p_id: str, dataverse_url: str, api_token: Optional[str] = None):
    """Fetches a dataset from a given Dataverse installation and persistent identifier.

    Args:
        p_id (str): Persistent Identifier of the dataset
        dataverse_url (str): URL to the dataverse installation to fetch the dataset from.

    Returns:
        Dict: Dataverse JSON as a dictionary representation
    """
    if dataverse_url.endswith("/"):
        dataverse_url = dataverse_url.rstrip("/")

    if api_token:
        api = NativeApi(dataverse_url, api_token)
    else:
        api = NativeApi(dataverse_url)

    # Download the dataset and retrieve the field data
    return api.get_dataset(p_id).json()


# ! STEP 2 UTILS: Creation of an on-the-fly object model
def create_block_definitions(block_name, block, dataverse_url):
    """Generates an object model based on the definition of a block.

    Args:
        block_name (str): Internal name of the metadatablock. This is not always the display name.
        block (Dict): Metadatablock definition from the Dataverse JSON dataset.
        dataverse_url (str): URL to the dataverse installation to fetch the block definition.

    Returns:
        DataverseBase: Empty object representation of the metadatablock.
    """
    # Get a lookup from the metadata config of the target DV
    lookup = _fetch_lookup(dataverse_url, block_name)

    # Initialize both definitions and add function dicts
    cls_def = {}
    add_funs = {}

    # Turn raw definitions into classes
    for field in block["fields"]:
        _process_field(field, lookup, cls_def, add_funs)

    # Now, create the class
    block_cls = create_model(
        block_name.capitalize(),
        __base__=(DataverseBase,),
        **cls_def,
    )()

    # Add metadatablock_name
    block_cls.__dict__["_metadatablock_name"] = block_name

    # TODO: Fix recursion problem with add_funs
    # Finally, add all add-functions
    # for name, function in add_funs.items():
    #    function = types.MethodType( function, block_cls )
    #    block_cls.__dict__[name] = function
    #    break

    return block_cls


def _fetch_lookup(dataverse_url: str, block_name: str):
    """Fetches the metadatablock definition from the Dataverse API

    This resulting definition is used to infer the correct names for
    the resulting fields. All other metadata for the fields such as
    'typeClass' etc. are drawn from the datasets Dataverse JSON.
    """
    url = f"{dataverse_url}/api/metadatablocks/{block_name}"
    response = requests.get(url)
    block_data = response.json()["data"]
    fields = {}

    return block_data["fields"]


def _process_field(field, lookup, cls_def, add_funs):
    """Processes a field according to its 'typeClass'."""

    PROCESS_MAPPING = {
        "primitive": _process_primitive,
        "controlledVocabulary": _process_primitive,
        "compound": _process_compound,
    }

    fun = PROCESS_MAPPING[field["typeClass"]]
    fun(field, lookup, cls_def, add_funs)


def _process_compound(field, lookup, cls_def, add_funs):
    """Processes a compound field and creates a new class from it."""

    _, description, cls = _create_compound_class(field, lookup)

    field_meta = copy.deepcopy(field)
    field_meta["description"] = description
    field_meta.pop("value")

    if field["multiple"]:
        dtype = List[cls]
        field_meta["default_factory"] = list
    else:
        dtype = Optional[cls]
        field_meta["default"] = None

    field_name = _clean_name(lookup[field["typeName"]]["title"])
    field_name = "".join([name.capitalize() for name in field_name.split(" ")])
    field_name = _camel_to_snake(field_name)

    # Generate add method
    add_funs[f"add_{field_name}"] = _generate_add_method(cls, field_name)

    cls_def[field_name] = (dtype, Field(**field_meta))


def _process_primitive(field, lookup, cls_def, add_funs):
    """Processes a primitive field and adds it to the metadatablock class definition"""

    name, primitive = _parse_primitive(field, lookup)
    cls_def[name] = primitive


def _create_compound_class(field, lookup):
    """Creates a compound class based on the primitives that it is made up from."""

    # Get metadata from lookup
    lookup = copy.deepcopy(lookup)
    field_meta = lookup[field["typeName"]]
    name = _clean_name(field_meta["title"])
    cls_name = _snake_to_camel(name.replace(" ", "_"))
    description = field_meta["description"]

    if "childFields" in field_meta:
        lookup = field_meta["childFields"]

    # Get all fields
    fields = _parse_compound_fields(field["value"], lookup)

    # Create the resulting class
    cls = create_model(cls_name, __base__=(DataverseBase,), **fields)

    cls.__name__ = cls_name

    # Create a new type from this
    return _clean_name(name), description, cls


def _parse_compound_fields(data: List, lookup):
    """Parses primitive fields found in a compound definition."""

    parsed_fields = {}

    for member in data:
        for primitive in member.values():
            name, field = _parse_primitive(primitive, lookup)

            parsed_fields[name] = field

    return parsed_fields


def _clean_name(name):
    """Removes anything that is not a valid variable name"""
    return re.sub(r"\-|\?|\(|\)|\[|\]|\.\\|\/|\&", "_", name)


def _parse_primitive(data: Dict, lookup: Dict):
    """Parses a primitive field. Returns name and field definition"""

    data = copy.deepcopy(data)
    data.pop("value")

    # Get metadata from lookup
    name = _camel_to_snake(lookup[data["typeName"]]["title"])
    name = "".join([n.capitalize() for n in name.split(" ")])
    name = _camel_to_snake(name)

    data["description"] = lookup[data["typeName"]]["description"]

    return (_clean_name(name), _create_primitive_field(lookup=lookup, **data))


def _create_primitive_field(lookup: Dict, **kwargs):
    """Creates a primtive PyDantic field used to assign to a class."""

    # Get type from lookup
    field_def = lookup[kwargs["typeName"]]
    dtype = field_def["type"]
    dtype = Types.get_mixed_type(dtype=dtype, multiple=kwargs["multiple"])

    if kwargs["multiple"]:
        kwargs["default_factory"] = list
    else:
        kwargs["default"] = None

    return (dtype, Field(**kwargs))


def _generate_add_method(target_cls, field):
    """Generates an add method that later on can be added to a target class to facilitate compound addition."""
    add_fun = copy.deepcopy(_generic_add_function)
    add_fun.__name__ = f"add_{field}"

    return forge.sign(
        forge.self,
        *[
            forge.kwarg(_clean_name(name), type=dtype, default=forge.empty)
            for name, dtype in target_cls.__annotations__.items()
        ],
        forge.kwarg("_target_cls", default=target_cls, bound=True),
        forge.kwarg("_field", default=field, bound=True),
    )(add_fun)


def _generic_add_function(self, **kwargs):
    """This is a generic function used as a template for add-funs"""
    target_cls = kwargs["_target_cls"]
    field = kwargs["_field"]
    kwargs.pop("_target_cls")
    kwargs.pop("_field")

    self.__dict__[field].append(target_cls(**kwargs))


def _camel_to_snake(name):
    """Turns 'CamelCase' to 'camel_case'"""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _snake_to_camel(name):
    """Turns 'snake_case' to 'SnakeCase'"""
    return "".join(x.capitalize() or "_" for x in name.split("_"))


def _clean_name(name):
    """Removes special characters from a name"""
    name = name.replace("-", "_")
    return re.sub(r"|\?|\(|\)|\[|\]|\.\\|\/|\&", "", name)


# ! STEP 3 UTILS: Assignment of the values to the generated data model
def populate_block_values(block_cls: DataverseBase, block_json: Dict):
    """Parses the given Dataverse JSON and assigns all values to the generated metadatablock object model.

    Args:
        block_cls (DataverseBase): Object representation of the block.
        block_json (Dict): JSON representation of the dataset's metadatablock.
    """

    for field in block_json:
        field_type = field["typeClass"]
        attr_name = _find_attribute(block_cls, field["typeName"])

        if field_type == "compound":
            for entry in field["value"]:
                sub_class = _get_sub_class(block_cls, attr_name)
                kwargs = {
                    _find_attribute(sub_class, name): compound["value"]
                    for name, compound in entry.items()
                }

                block_cls.__dict__[attr_name].append(sub_class(**kwargs))

        else:
            block_cls.__dict__[attr_name] = field["value"]


def _find_attribute(block, typeName):
    """Finds the corresponding attribute name of the Dataverse field"""
    for name, field in block.__fields__.items():
        if typeName == field.field_info.extra["typeName"]:
            return name

    raise AttributeError(f"Cant locate attribute with 'typeName = {typeName}'.")


def _get_sub_class(block, field_name):
    """Returns the sub class of a compound field in order to add data."""
    return block.__fields__[field_name].type_
