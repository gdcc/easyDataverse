import os
import tqdm
import sys

from typing import Callable, List, Dict

from pyDataverse.api import DataAccessApi
from easyDataverse.core.file import File


def field_parser_factory(field_type: str) -> Callable:
    """Manages the parsing of specific fields"""

    mapping = {
        "compound": parse_compound,
        "primitive": parse_primitive,
        "controlledVocabulary": parse_primitive,
    }

    return mapping[field_type]


def parse_primitive(field: dict, module):
    """Parses a primtive field by checking the API schema."""

    # Get module properties
    properties = module.schema()["properties"]

    return {
        attr_name: field["value"]
        for attr_name, property in properties.items()
        if property["typeName"] == field["typeName"]
    }


def parse_compound(field: dict, module):
    """Parses a compound field by checking the module schema to a list of JSON objects"""

    # Retrieve the definitions from the module schema
    compound_name, field_mapping = _get_compound_definitions(module, field["typeName"])

    return {
        compound_name: [
            {
                field_mapping[type_name]: sub_field["value"]
                for type_name, sub_field in obj.items()
            }
            for obj in field["value"]
        ]
    }


def _get_compound_definitions(module, type_name: str):
    """Retrieves the compound definitions found in the module schema."""

    for obj_name, property in module.schema()["properties"].items():
        compound_name = property["typeName"]

        if compound_name == type_name:

            definition_name = property["items"]["$ref"].split("/")[-1]
            definition = module.schema()["definitions"][definition_name]["properties"]

            # Create a mapping from typeName to actual attribute name
            mapping = {
                field["typeName"]: attr_name for attr_name, field in definition.items()
            }

            return obj_name, mapping

    raise NameError(
        f"Field with typeName {type_name} is not defined in module {module.__name__}"
    )


def download_files(
    data_api: DataAccessApi, dataset, files_list: List[Dict], filedir: str
) -> None:
    """Downloads and adds all files given in the dataset to the Dataset-Object"""

    # Set up the progress bar
    files_list = tqdm.tqdm(files_list, file=sys.stdout)
    files_list.set_description(f"Downloading data files")

    for file in files_list:

        # Get file metdata
        filename = file["dataFile"]["filename"]
        file_pid = file["dataFile"]["id"]

        description = file["dataFile"].get("description")
        directory_label = file.get("directoryLabel")

        if filedir is not None:
            # Get the content
            response = data_api.get_datafile(file_pid)

            if response.status_code != 200:
                raise FileNotFoundError(f"No content found for file {filename}.")

            # Create local path for later upload
            if directory_label:
                filename = os.path.join(directory_label, filename)

            local_path = os.path.join(filedir, filename)

            # Write content to local file
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(response.content)
        else:
            local_path = None

        # Create the file object
        datafile = File(
            filename=filename,
            description=description,
            local_path=local_path,
            file_pid=file_pid,
        )

        print(datafile)

        dataset.files.append(datafile)
