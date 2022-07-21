import json
import os
import importlib
import importlib.util
import inspect
import pandas as pd
import sys

from pathlib import Path
from enum import EnumMeta
from tempfile import TemporaryDirectory
from typing import Callable, List, Tuple
from datamodel_code_generator import InputFileType, generate
from jinja2 import Template
from importlib import resources as pkg_resources


from easyDataverse.tools.codegen import templates as jinja_templates
from easyDataverse.tools.codegen.schema import (
    split_metadatablock,
    generate_JSON_schema,
    camel_to_snake,
)


def generate_metadatablock_code(path: str, out: str, schema_loc: str) -> None:
    """Generater the code for a metadatablock based on pyDantic"""

    metadatablock_name = open(path, "r").readlines()[1]
    metadatablock_name = metadatablock_name.split("\t")[1]
    metadatablock_name = metadatablock_name[0].lower() + metadatablock_name[1::]

    metadatablock = pd.read_csv(path, sep="\t", skiprows=2, usecols=range(16))

    # TODO Fix TSV rather than the columns in the code
    metadatablock.columns = [col.strip() for col in metadatablock.columns]

    # Extract all informations
    fields, controlled_vocab = split_metadatablock(metadatablock)
    properties, definitions, required = generate_JSON_schema(
        fields, metadatablock_name, controlled_vocab
    )

    # Generate JSON schema
    filename = f"{metadatablock_name}.json"
    json_schema = {
        "$id": filename,
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": metadatablock_name,
        "type": "object",
        "properties": properties,
        "definitions": definitions,
        "required": required,
    }

    schema_path = os.path.join(schema_loc, f"{metadatablock_name}.json")
    with open(schema_path, "w") as f:
        f.write(json.dumps(json_schema, indent=2))

    # Generate the raw code of the metadatablock
    generated_code = generate_code(json_schema)

    # Write code to file to read it afterwards
    module_name = f"{metadatablock_name}.py"
    out_path = os.path.join(out, module_name)

    with open(out_path, "w") as f:
        f.write(generated_code)

    # Convert code to a module to get all sub classes it
    sys.path.append(out)
    code_module = importlib.import_module(metadatablock_name)
    clsmembers = inspect.getmembers(code_module, inspect.isclass)

    for name, obj in clsmembers:
        if name == "DataverseBase":
            continue

        elif obj.__name__.lower() == metadatablock_name.lower():
            continue

        elif isinstance(obj, EnumMeta):
            continue

        generated_code += generate_add_function(obj)

    with open(out_path, "w") as f:
        f.write(clean_code(generated_code))


def generate_code(json_schema: dict) -> str:
    """Generates pyDantic code from a JSON schema."""

    with TemporaryDirectory() as temporary_directory_name:
        temporary_directory = Path(temporary_directory_name)
        output = Path(temporary_directory / "model.py")
        generate(
            json.dumps(json_schema),
            base_class="easyDataverse.core.DataverseBase",
            input_file_type=InputFileType.JsonSchema,
            input_filename=json_schema["$id"],
            output=output,
            field_include_all_keys=True,
            use_standard_collections=False,
            snake_case_field=True,
            reuse_model=True,
            use_schema_description=True,
        )

        return output.read_text()


def clean_code(code: str) -> str:
    """Replaces certain parts of the code, which cannot be enforced via the generator"""

    # Mapping used for replacement
    replace_map = [
        ("...", "default_factory=list"),
        ("type_class", "typeClass"),
        ("type_name", "typeName"),
        ("from core", "from easyDataverse.core"),
    ]

    for replacement in replace_map:
        code = code.replace(*replacement)

    return code


def generate_add_function(cls: Callable) -> str:
    """Generates an add function which will be added to the metadatablock's main class."""

    field = camel_to_snake(cls.__name__)
    definitions = generate_definition(cls)
    summary, args_doc = generate_docstring(cls)
    params = generate_arguments(cls)

    template = Template(pkg_resources.read_text(jinja_templates, "add_function.jinja2"))

    return template.render(
        field=field,
        definitions=definitions,
        summary=summary,
        args_doc=args_doc,
        class_name=cls.__name__,
        params=params,
    )


def generate_definition(cls: Callable) -> List[str]:
    """Generates a function signature from a pyDantic class object"""

    # Fetch parameters
    params = cls.__annotations__

    return [
        f"{name}: {data_type},"
        if "Optional" not in data_type
        else f"{name}: {data_type} = None,"
        for name, data_type in params.items()
    ]


def generate_docstring(cls: Callable) -> Tuple[str, List[str]]:
    """Generates a Google styled docstring for the add functionality"""

    # Get the properties for all fields
    properties = cls.schema()["properties"]

    # Short generic summary
    summary = (
        f"Function used to add an instance of {cls.__name__} to the metadatablock."
    )

    # Generate individual args lines with descriptions
    args_doc = [
        f"{camel_to_snake(name)} ({field['type']}): {field['description']}"
        if field.get("type")
        else f"{camel_to_snake(name)} (Enum): {field['description']}"
        for name, field in properties.items()
    ]

    # TODO Handle Enums better

    return summary, args_doc


def generate_arguments(cls: Callable) -> str:
    """Generates the arguments that are passed to the class that is about to be instantiated."""

    # Fetch parameters
    params = cls.__signature__.parameters

    return ", ".join(
        [f"{camel_to_snake(param)}={camel_to_snake(param)}" for param in params.keys()]
    )
