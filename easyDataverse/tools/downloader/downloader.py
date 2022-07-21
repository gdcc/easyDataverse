import os

from typing import Tuple

from pyDataverse.api import NativeApi, DataAccessApi
from easyDataverse.tools.utils import get_class
from easyDataverse.tools.downloader.libutils import field_parser_factory, download_files
from easyDataverse.tools.downloader.nolibutils import (
    fetch_dataset,
    create_block_definitions,
    populate_block_values,
)


def download_from_dataverse_with_lib(
    dataset,
    doi: str,
    lib_name: str,
    filedir: str,
    dataverse_url: str = "",
    api_token: str = "",
):
    """Downloads a dataset from a Dataverse instance and initializes a Dataset object.

    Args:
        dataset (Dataset): Empty dataset to which will be written.
        doi (str): Peristent identifier of the dataset.
        lib_name (str): Used to infer the metadata scheme from a library that holds all metadatablocks.
        filedir (str): Destination where the files will be downloaded.
        dataverse_url (str): URL to the Dataverse installation. Can be inferred from env vars.
        api_token (str): API Token used to authorize at the dataverse installation. Can be inferred from env vars.
    """

    # Intialize the pyDataverse instance to fetch the dataset
    api = NativeApi(dataverse_url, api_token)

    # Download the dataset and retrieve the field data
    dv_dataset = api.get_dataset(doi)
    json_data = dv_dataset.json()["data"]["latestVersion"]["metadataBlocks"]
    dataset.p_id = doi

    # Build new mapping
    data = {}

    for block_name, block in json_data.items():

        module_path = f".metadatablocks.{block_name[0].lower() + block_name[1::]}"

        _, module = get_class(module_path, lib_name)

        fields = block["fields"]
        data = {}

        for field in fields:
            parser_fun = field_parser_factory(field["typeClass"])
            data.update(parser_fun(field, module))

        # Initialize the module
        dataset.add_metadatablock(module.parse_obj(data))

    # Add all files present in the dataset
    files_list = dv_dataset.json()["data"]["latestVersion"]["files"]
    data_api = DataAccessApi(dataverse_url, api_token)
    download_files(data_api, dataset, files_list, filedir)

    return dataset


def download_from_dataverse_without_lib(
    dataset, doi: str, filedir: str, dataverse_url: str, api_token: str
):
    """Downloads and initializes a dataset from a dataverse URL and persistent identifier.

    This method infers the metadatablocks from the URL and dataset JSON. In contrast,
    to the function 'download_from_dataverse_with_lib' this one does only contain
    fields that are present in the dataset and thus does not contain the COMPLETE
    metadatablocks. Yet, the dataset will still produc a valid Dataverse JSON that
    can be used to upload and update datasets.

    Args:
        dataset (Dataset): Dataset object where files and metadata are stored.
        doi (str): Peristent identifier of the dataset.
        filedir (str): Destination where the files will be downloaded.
        dataverse_url (str): URL to the Dataverse installation. Can be inferred from env vars.
        api_token (str): API Token used to authorize at the dataverse installation. Can be inferred from env vars.
    """

    # Step 1: Fetch data from the Dataverse installation and get blocks
    dv_dataset = fetch_dataset(doi, dataverse_url, api_token)
    metadatablocks = dv_dataset["data"]["latestVersion"]["metadataBlocks"]
    dataset.p_id = doi

    # Step 2: Extract all metadatablocks from the given dataset
    blocks = [
        create_block_definitions(block_name, block, dataverse_url)
        for block_name, block in metadatablocks.items()
    ]

    # Step 3: Populate data and assign to dataset
    for block in blocks:
        block_name = block._metadatablock_name
        populate_block_values(block, metadatablocks[block_name]["fields"])
        dataset.add_metadatablock(block)

    # Step 4: Fetch files and add them to the dataset
    files_list = dv_dataset["data"]["latestVersion"]["files"]
    data_api = DataAccessApi(dataverse_url, api_token)
    download_files(data_api, dataset, files_list, filedir)

    return dataset
