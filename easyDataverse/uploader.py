from urllib.parse import urljoin
import httpx

from rich.panel import Panel
from rich.console import Console
from typing import Dict, List, Optional, Union
from dvuploader import File, DVUploader

from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset

from easyDataverse.license import CustomLicense, License


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

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)  # type: ignore
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

    response = api.create_dataset(**create_params)  # type: ignore
    response.raise_for_status()

    # Get response data
    p_id = response.json()["data"]["persistentId"]

    _uploadFiles(
        files=files,
        p_id=p_id,  # type: ignore
        api=api,  # type: ignore
        n_parallel=n_parallel,
    )  # type: ignore

    console = Console()
    url = urljoin(DATAVERSE_URL, f"dataset.xhtml?persistentId={p_id}")  # type: ignore
    panel = Panel(
        f"🎉 {url}",
        title="Dataset URL",
        border_style="green",
        title_align="left",
        padding=(1, 2),
    )

    print("\n")
    console.print(panel)

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
    license: Optional[Union[CustomLicense, License]] = None,
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

    if license is not None:
        _update_license(
            p_id=p_id,
            license=license,
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
        httpx.HTTPError: If the request fails.
    """

    EDIT_ENDPOINT = f"{base_url.rstrip('/')}/api/datasets/:persistentId/editMetadata?persistentId={p_id}&replace=true"
    headers = {"X-Dataverse-key": api_token}

    response = httpx.put(EDIT_ENDPOINT, headers=headers, json=to_change)
    response.raise_for_status()


def _update_license(
    p_id: str,
    license: Union[CustomLicense, License],
    base_url: str,
    api_token: str,
):
    """Updates the license of a dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        license (Union[CustomLicense, License]): License object to update.
        base_url (str): URL of the dataverse instance.
        api_token (str): API token of the user.

    Raises:
        AssertionError: If license is not a License or CustomLicense instance.
        Exception: If the JSON-LD metadata update fails.
    """
    assert isinstance(license, (License, CustomLicense)), (
        "License must be a License or CustomLicense"
    )

    headers = {
        "X-Dataverse-key": api_token,
        "Accept": "application/ld+json",
        "Content-Type": "application/ld+json",
    }

    # First, fetch the JSON-LD metadata
    data = _fetch_json_ld_metadata(
        p_id=p_id,
        base_url=base_url,
        headers=headers,
    )

    if isinstance(license, CustomLicense):
        for field in License.json_ld_field_names():
            data.pop(field, None)
        data.update(license.to_json_ld())
    else:
        for field in CustomLicense.json_ld_field_names():
            data.pop(field, None)
        data.update(license.to_json_ld())

    # Then, update the JSON-LD metadata on the server
    _update_json_ld_metadata(
        p_id=p_id,
        data=data,
        base_url=base_url,
        headers=headers,
    )


def _fetch_json_ld_metadata(
    p_id: str,
    base_url: str,
    headers: Dict[str, str],
):
    """Fetches JSON-LD metadata for a dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        base_url (str): URL of the dataverse instance.
        headers (Dict[str, str]): HTTP headers including API token.

    Returns:
        Dict: The JSON-LD metadata for the dataset.

    Raises:
        httpx.HTTPError: If the request fails.
        AssertionError: If the response doesn't contain expected data structure.
    """
    response = httpx.get(
        f"{base_url.rstrip('/')}/api/datasets/:persistentId/metadata?persistentId={p_id}",
        headers=headers,
    )
    response.raise_for_status()
    content = response.json()
    assert "data" in content

    return content["data"]


def _update_json_ld_metadata(
    p_id: str,
    data: Dict,
    base_url: str,
    headers: Dict[str, str],
):
    """Updates JSON-LD metadata for a dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        data (Dict): The JSON-LD metadata to update.
        base_url (str): URL of the dataverse instance.
        headers (Dict[str, str]): HTTP headers including API token.

    Returns:
        Dict: The response from the server.

    Raises:
        Exception: If the update fails (status code != 200).
    """
    response = httpx.put(
        f"{base_url.rstrip('/')}/api/datasets/:persistentId/metadata?persistentId={p_id}&replace=true",
        headers=headers,
        json=data,
    )

    if response.status_code != 200:
        raise httpx.HTTPError(f"Failed to update JSON-LD metadata: {response.text}")

    return response.json()
