import os
import sys
from typing import Dict, List, Optional

import tqdm
from pyDataverse.api import DataAccessApi
import yaml

from dvuploader import File


class YAMLDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)


def download_files(
    data_api: DataAccessApi,
    dataset,
    files_list: List[Dict],
    filedir: str,
    filenames: Optional[List[str]] = None,
) -> None:
    """Downloads and adds all files given in the dataset to the Dataset-Object"""

    if filedir is not None:
        # Set up the progress bar
        files_list = tqdm.tqdm(files_list, file=sys.stdout)  # type: ignore
        files_list.set_description(f"Downloading data files")  # type: ignore

    for file in files_list:
        # Get file metdata
        filename = file["dataFile"]["filename"]
        file_pid = file["dataFile"]["id"]

        if filenames is not None and filename not in filenames:
            # Just download the necessary files
            continue

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
            local_path = f"./{filename}"

        # Create the file object
        datafile = File(
            filepath=local_path,
            description=description,
            file_id=file_pid,
        )

        dataset.files.append(datafile)
