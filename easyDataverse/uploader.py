import os
import tempfile
import requests
import pandas as pd

from urllib.parse import urljoin
from typing import Dict, List, Optional
from dvuploader import File, DVUploader

from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset

from easyDataverse.tabdata import TabData


def upload_to_dataverse(
    json_data: str,
    dataverse_name: str,
    DATAVERSE_URL: str,
    API_TOKEN: Optional[str] = None,
    files: List[File] = [],
    tabular_data: Dict[str, TabData] = {},
    p_id: Optional[str] = None,
    n_parallel: int = 1,
) -> str:
    """Uploads a given Dataset to the dataverse installation found in the environment variables.

    Args:
        json_data (str): JSON representation of the Dataverse dataset.
        dataverse_name (str): Name of the Dataverse where the data will be uploaded to.
        files (List[str], optional): List of files that should be uploaded. Can also include durectory names. Defaults to None.
        p_id (Optional[str], optional): Persitent Identifier of the dataset. Defaults to None.


    Raises:
        ValueError: If the API Token is missing.
    Returns:
        str: The resulting DOI of the dataset, if successful.
    """

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)
    ds = Dataset()
    ds.from_json(json_data)

    # Finally, validate the JSON
    if not ds.validate_json():
        raise ValueError("JSON is not valid")

    create_params = {
        "dataverse": dataverse_name,
        "metadata": json_data,
    }

    if p_id:
        create_params["pid"] = p_id

    response = api.create_dataset(**create_params)
    response.raise_for_status()

    # Get response data
    p_id = response.json()["data"]["persistentId"]

    with tempfile.TemporaryDirectory() as temp_dir:

        tabular_files = _write_tabular_data(tabular_data, temp_dir)
        _uploadFiles(
            files=files + tabular_files,
            p_id=p_id,
            api=api,
            n_parallel=n_parallel,
        )  # type: ignore

    print(f"{DATAVERSE_URL}/dataset.xhtml?persistentId={p_id}")

    return p_id  # type: ignore


def _initialize_pydataverse(DATAVERSE_URL: str, API_TOKEN: str):
    """Sets up a pyDataverse API for upload."""
    return (
        NativeApi(DATAVERSE_URL, API_TOKEN),
        DataAccessApi(DATAVERSE_URL, API_TOKEN),
    )


def _write_tabular_data(
    tabular_data: Dict[str, TabData],
    temp_dir: str,
) -> List[File]:
    """
    Writes tabular data to temporary files and prepares them for upload.

    Args:
        tabular_data (Dict[str, TabData]): A dictionary containing tabular data
            where the keys are the names of the tables and the values are instances
            of the TabData class.
        temp_dir (str): The path to the temporary directory where the files will be written.

    Returns:
        List[File]: A list of File objects representing the prepared files.

    """
    return [tab_data.prepare_upload(temp_dir) for tab_data in tabular_data.values()]


def _uploadFiles(
    files: List[File],
    p_id: str,
    api: DataAccessApi,
    n_parallel: int = 1,
) -> None:
    """Uploads any file to a dataverse dataset.
    Args:
        filename (String): Path to the file
        p_id (String): Dataset permanent ID to upload.
        api (API): API object which is used to upload the file
    """

    if not files:
        return

    dvuploader = DVUploader(files=files)
    dvuploader.upload(
        persistent_id=p_id,
        dataverse_url=api.base_url,
        api_token=api.api_token,
        n_parallel_uploads=n_parallel,
    )


def update_dataset(
    p_id: str,
    json_data: dict,
    files: List[File],
    tabular_data: Dict[str, TabData],
    DATAVERSE_URL: Optional[str] = None,
    API_TOKEN: Optional[str] = None,
) -> bool:
    """Uploads and updates the metadata of a draft dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        json_data (dict): Dataverse JSON representation of the dataset.
        files (List[File]): List of files that should be uploaded. Can also include directory names.
        DATAVERSE_URL (Optional[str], optional): The URL of the Dataverse instance. Defaults to None.
        API_TOKEN (Optional[str], optional): The API token for authentication. Defaults to None.

    Returns:
        bool: True if the dataset was successfully updated, False otherwise.
    """
    url = urljoin(
        DATAVERSE_URL,  # type: ignore
        f"/api/datasets/:persistentId/versions/:draft?persistentId={p_id}",
    )

    response = requests.put(
        url,
        json=json_data,
        headers={"X-Dataverse-key": API_TOKEN},  # type: ignore
    )

    response.raise_for_status()
    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)

    with tempfile.TemporaryDirectory() as temp_dir:
        tabular_files = _write_tabular_data(tabular_data, temp_dir)
        _uploadFiles(
            files=files + tabular_files,
            p_id=p_id,
            api=api,  # type: ignore
        )

    return True
