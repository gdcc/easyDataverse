import os
import sys
from typing import Dict, List

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
) -> None:
    """Downloads and adds all files given in the dataset to the Dataset-Object"""

    if len(files_list) == 0:
        return

    if filedir is not None:
        # Set up the progress bar
        files_list = tqdm.tqdm(files_list, file=sys.stdout)  # type: ignore
        files_list.set_description(f"Downloading data files")  # type: ignore

    for file in files_list:

        # Get file metdata
        filename = file["dataFile"]["filename"]
        file_pid = file["dataFile"]["id"]
        directory_label = file.get("directoryLabel", "")

        if filedir:
            local_path = os.path.join(filedir, directory_label, filename)
        else:
            local_path = os.path.join(filedir, filename)

        response = data_api.get_datafile(file_pid)
        response.raise_for_status()

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(response.content)

        datafile = File(
            filepath=local_path,
            file_id=str(file_pid),
            **file,
        )

        dataset.files.append(datafile)
