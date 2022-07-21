import io
import os
import json
import requests
import sys
import tqdm
import zipfile

from typing import List, Optional

from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataset, Datafile

from easyDataverse.core.file import File
from easyDataverse.core.exceptions import (
    MissingURLException,
    MissingCredentialsException,
)


def upload_to_dataverse(
    json_data: str,
    dataverse_name: str,
    files: List[File] = [],
    p_id: Optional[str] = None,
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
        MissingURLException: URL to the dataverse installation is missing. Please include in your environment variables.
        MissingCredentialsException: API-Token to the dataverse installation is missing. Please include in your environment variables

    Returns:
        str: The resulting DOI of the dataset, if successful.
    """

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)
    ds = Dataset()
    ds.from_json(json_data)

    # Finally, validate the JSON
    if ds.validate_json():
        if p_id:
            # Update dataset if pid given
            response = api.create_dataset(dataverse_name, json_data, p_id)
        else:
            # Create new if no pid given
            response = api.create_dataset(dataverse_name, json_data)

        if response.json()["status"] != "OK":
            raise Exception(response.json()["message"])

        # Get response data
        p_id = response.json()["data"]["persistentId"]

        if files:
            __uploadFiles(files, p_id, api, content_loc)

        print(f"{os.environ['DATAVERSE_URL']}/dataset.xhtml?persistentId={p_id}")

        return p_id

    else:
        raise Exception("Could not upload")


def _initialize_pydataverse(DATAVERSE_URL: Optional[str], API_TOKEN: Optional[str]):
    """Sets up a pyDataverse API for upload."""

    # Get environment variables
    if DATAVERSE_URL is None:
        try:
            DATAVERSE_URL = os.environ["DATAVERSE_URL"]

        except KeyError:
            raise MissingURLException

    if API_TOKEN is None:
        try:
            API_TOKEN = os.environ["DATAVERSE_API_TOKEN"]
        except KeyError:
            raise MissingCredentialsException

    return NativeApi(DATAVERSE_URL, API_TOKEN), DataAccessApi(DATAVERSE_URL, API_TOKEN)


def __uploadFiles(
    files: List[File], p_id: str, api: DataAccessApi, content_loc: Optional[str] = None
) -> None:
    """Uploads any file to a dataverse dataset.
    Args:
        filename (String): Path to the file
        p_id (String): Dataset permanent ID to upload.
        api (API): API object which is used to upload the file
    """

    # Compress all files present in a ZipFile
    zip_file = io.BytesIO()
    has_content = False

    # Set up a progress bar
    files = tqdm.tqdm(files, file=sys.stdout)
    files.set_description(f"Uploading data files")

    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            if file.local_path and not file.file_pid:
                has_content = True
                zf.writestr(file.filename, open(file.local_path, "rb").read())

    # Write to the zip
    filename = "contents.zip"

    if content_loc:
        # Create destination dir to store upload package
        os.makedirs(content_loc, exist_ok=True)
        filename = os.path.join(content_loc, filename)

    with open(filename, "wb") as f:
        f.write(zip_file.getvalue())

    df = Datafile()
    df.set({"pid": p_id, "filename": filename})

    if has_content:
        response = api.upload_datafile(p_id, filename, df.json())

        if response.status_code != 200:
            raise ValueError(f"Upload failed: {response.status_code} {response.text}")

    if content_loc is None:
        os.remove(filename)


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

    url = f"{os.environ['DATAVERSE_URL']}/api/datasets/:persistentId/versions/:draft?persistentId={p_id}"
    response = requests.put(
        url,
        json=json_data,
        headers={"X-Dataverse-key": os.environ["DATAVERSE_API_TOKEN"]},
    )

    if response.json()["status"] != "OK":
        raise Exception(response.json()["message"])

    api, _ = _initialize_pydataverse(DATAVERSE_URL, API_TOKEN)

    # Update files that have a pid
    for file in files:
        if not file.file_pid:
            continue

        # Get the metadata of the file
        file_dir = os.path.dirname(file.filename)

        response = api.replace_datafile(
            identifier=file.file_pid,
            filename=file.local_path,
            json_str=json.dumps(
                {
                    "description": file.description,
                    "forceReplace": True,
                    "directoryLabel": file_dir,
                }
            ),
            is_filepid=False,
        )

    # Upload files that havent been added yet
    __uploadFiles(files, p_id, api, content_loc)

    return True
