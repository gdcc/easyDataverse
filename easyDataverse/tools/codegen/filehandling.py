import inspect
import importlib
import importlib.util

from pathlib import Path
from typing import Tuple


def create_init_line_library(module_path: str, lib_name: str) -> str:
    """Creates an __init__ entry of the library dir for the corresponding metadatablocks file"""

    # Get the module name from file
    module_name = Path(module_path).stem

    # Import package to inspect it
    module = importlib.import_module(module_name)

    # Get the class that will be part of the init
    for class_name, _ in inspect.getmembers(module, inspect.isclass):

        if class_name.lower() == module_name.lower():
            return (
                f"from {lib_name}.metadatablocks import {class_name}"
            )

    raise ModuleNotFoundError(
        f"Could not find module '{module_name}' in generated modules."
    )


def create_init_line_metadatblock(module_path: str, lib_name: str) -> str:
    """Creates an __init__ entry of the metadatablocks dir for the corresponding metadatablocks file"""

    # Get the module name from file
    module_name = Path(module_path).stem

    # Import package to inspect it
    module = importlib.import_module(module_name, module_path)

    # Get the class that will be part of the init
    for class_name, _ in inspect.getmembers(module, inspect.isclass):

        if class_name.lower() == module_name.lower():
            return (
                f"from {lib_name}.metadatablocks.{module_name} import {class_name}"
            )

    raise ModuleNotFoundError(
        f"Could not find module '{module_name}' in generated modules."
    )


def generate_template(module_path: str) -> Tuple[str, dict]:
    """Generates templates which can be used to map from arbitrary file formats to Dataverse"""

    # Get the module name from file
    module_name = Path(module_path).stem

    # Import package to inspect it
    module = importlib.import_module(module_name, module_path)

    # Get the class that will be part of the init
    for class_name, class_obj in inspect.getmembers(module, inspect.isclass):
        if class_name.lower() == module_name.lower():
            return class_name, {
                class_name: class_to_empty_dict(class_obj)
            }

    raise ModuleNotFoundError(
        f"Could not find module '{module_name}' in generated modules."
    )


def class_to_empty_dict(cls) -> dict:
    """Generates a dictionary with 'None' fields which can be used for mapping."""

    data_model, array_fields, single_fields = {}, {}, {}
    for field_name, field in cls.__fields__.items():
        try:
            # Parse compound fields
            subclass_properties = field.type_.schema()["properties"]
            array_fields.update(
                {field_name: [{
                    attribute: None
                    for attribute in subclass_properties.keys()
                }]
                }
            )
        except AttributeError:
            # Parse primitive fields
            single_fields.update(
                {field_name: None}
            )

    # Merge both to have single fields on top and array fields bottom
    data_model.update(single_fields)
    data_model.update(array_fields)

    return data_model
