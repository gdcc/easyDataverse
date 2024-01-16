import os
import json
import requests

from urllib.parse import urljoin
from typing import List, Optional
from dvuploader import File, DVUploader

from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset


def upload_to_dataverse(
    json_data: str,
    dataverse_name: str,
    files: List[File] = [],
    p_id: Optional[str] = None,
    n_parallel: int = 1,
    content_loc: Optional[str] = None,
    DATAVERSE_URL: Optional[str] = None,
    API_TOKEN: Optional[str] = None,
) -> str:
    """Uploads a given Dataset to the dataverse installation found in the environment variables.

    Args:
        json_data (str): JSON representation of the Dataverse dataset.
        dataverse_name (str): Name of the Dataverse where the data will be uploaded to.
        files (List[str], optional): List of files that should be uploaded. Can also include durectory names. Defaults to None.
        p_id (Optional[str], optional): Persitent Identifier of the dataset. Defaults to None.
        content_loc (Optional[str]): If specified, the ZIP that is used to upload will be stored at the destination provided. Defaults to None.


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

    print(f"{DATAVERSE_URL}/dataset.xhtml?persistentId={p_id}")

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
    json_data: dict,
    files: List[File],
    content_loc: Optional[str] = None,
    DATAVERSE_URL: Optional[str] = None,
    API_TOKEN: Optional[str] = None,
) -> bool:
    """Uploads and updates the metadata of a draft dataset.

    Args:
        p_id (str): Persistent ID of the dataset.
        json_data (dict): Dataverse JSON representation of the dataset.
                files (List[str], optional): List of files that should be uploaded. Can also include durectory names. Defaults to None.

        content_loc (Optional[str], optional): If specified, the ZIP that is used to upload will be stored at the destination provided. Defaults to None.
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

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)  # type: ignore

    # Update files that have a pid
    new_files = []
    for file in files:
        if not file.file_id:
            new_files.append(file)
            continue

        # Get the metadata of the file
        file_dir = os.path.dirname(file.filepath)

        if file.filepath is not None:
            response = api.replace_datafile(
                identifier=file.file_id,
                filename=file.fileName,
                json_str=json.dumps(
                    {
                        "description": file.description,
                        "forceReplace": True,
                        "directoryLabel": file_dir,
                    }
                ),
                is_filepid=False,
            )

    _uploadFiles(
        files=new_files,
        p_id=p_id,
        api=api,  # type: ignore
    )

    return True
