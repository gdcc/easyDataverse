import requests

from typing import Dict, List, Optional
from dvuploader import File, DVUploader

from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset


def upload_to_dataverse(
    json_data: str,
    dataverse_name: str,
    files: List[File] = [],
    p_id: Optional[str] = None,
    n_parallel: int = 1,
    DATAVERSE_URL: Optional[str] = None,
    API_TOKEN: Optional[str] = None,
) -> str:
    """Uploads a given Dataset to the dataverse installation found in the environment variables.

    Args:
        json_data (str): JSON representation of the Dataverse dataset.
        dataverse_name (str): Name of the Dataverse where the data will be uploaded to.
        files (List[str], optional): List of files that should be uploaded. Can also include directory names. Defaults to None.
        p_id (Optional[str], optional): Persistent Identifier of the dataset. Defaults to None.


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

    _uploadFiles(
        files=files,
        p_id=p_id,
        api=api,
        n_parallel=n_parallel,
    )  # type: ignore

    return p_id  # type: ignore


def _initialize_pydataverse(DATAVERSE_URL: str, API_TOKEN: str):
    """Sets up a pyDataverse API for upload."""
    return (
        NativeApi(DATAVERSE_URL, API_TOKEN),
        DataAccessApi(DATAVERSE_URL, API_TOKEN),
    )


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
    to_change: Dict,
    files: List[File],
    DATAVERSE_URL: Optional[str] = None,
    API_TOKEN: Optional[str] = None,
) -> bool:
    """Uploads and updates the metadata of a draft dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        to_change (Dict): Dictionary of fields to change.
        files (List[File]): List of files that should be uploaded. Can also include directory names.
        DATAVERSE_URL (Optional[str], optional): The URL of the Dataverse instance. Defaults to None.
        API_TOKEN (Optional[str], optional): The API token for authentication. Defaults to None.

    Returns:
        bool: True if the dataset was successfully updated, False otherwise.
    """

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)  # type: ignore

    _update_metadata(
        p_id=p_id,
        to_change=to_change,
        base_url=DATAVERSE_URL,  # type: ignore
        api_token=API_TOKEN,  # type: ignore
    )

    _uploadFiles(
        files=files,
        p_id=p_id,
        api=api,  # type: ignore
    )

    return True


def _update_metadata(
    p_id: str,
    to_change: Dict,
    base_url: str,
    api_token: str,
):
    """Updates the metadata of a dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        to_change (Dict): Dictionary of fields to change.
        base_url (str): URL of the dataverse instance.
        api_token (str): API token of the user.

    Raises:
        requests.HTTPError: If the request fails.
    """
    EDIT_ENDPOINT = f"{base_url.rstrip('/')}/api/datasets/:persistentId/editMetadata?persistentId={p_id}&replace=true"
    headers = {"X-Dataverse-key": api_token}

    response = requests.put(EDIT_ENDPOINT, headers=headers, json=to_change)

    response.raise_for_status()
