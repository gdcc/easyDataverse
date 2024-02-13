import asyncio
import os
from typing import Dict, List
import aiofiles
import aiohttp
import rich

from rich.progress import Progress, TaskID
from pyDataverse.api import DataAccessApi
import yaml

from dvuploader import File

CHUNK_SIZE = 10 * 1024**2  # 10 MB
MAXIMUM_DISPLAYED_FILES = 40


class YAMLDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)


async def download_files(
    data_api: DataAccessApi,
    files_list: List[Dict],
    filedir: str,
    filenames: List[str],
    n_parallel_downloads: int,
) -> List[File]:
    """Downloads and adds all files given in the dataset to the Dataset-Object"""

    files_list = _filter_files(files_list, filenames)
    progress, task_ids = setup_progress_bars(files=files_list)
    over_threshold = len(files_list) > MAXIMUM_DISPLAYED_FILES

    if len(files_list) == 0:
        return []

    if data_api.api_token:
        headers = {"X-Dataverse-key": data_api.api_token}
    else:
        headers = {}

    connector = aiohttp.TCPConnector(limit=n_parallel_downloads)
    async with aiohttp.ClientSession(
        base_url=data_api.base_url,
        connector=connector,
        headers=headers,
    ) as session:

        with progress:
            rich.print("\n[bold]Downloading files[/bold]\n")

            tasks = [
                _download_file(
                    session=session,
                    file=file,
                    filedir=filedir,
                    progress=progress,
                    task_id=task_id,
                    over_threshold=over_threshold,
                )
                for file, task_id in zip(files_list, task_ids)
            ]

            files = await asyncio.gather(*tasks)

    rich.print("\n[bold]✅ Done [/bold]\n\n")

    return files


def setup_progress_bars(
    files: List[Dict],
):
    """
    Sets up progress bars for each file.

    Returns:
        A list of progress bars, one for each file.
    """

    tasks = []
    progress = Progress()

    for file in files:

        filename = file["dataFile"]["filename"]
        filesize = file["dataFile"]["filesize"]
        directory_label = file.get("directoryLabel", "")
        filepath = os.path.join(directory_label, filename)

        tasks.append(
            setup_pbar(
                fpath=filepath,
                filesize=filesize,
                progress=progress,
            )
        )

    return progress, tasks


def setup_pbar(
    fpath: str,
    filesize: int,
    progress: Progress,
) -> int:
    """
    Set up a progress bar for a file.

    Args:
        fpath (str): The path to the file.
        progress (Progress): The progress bar object.

    Returns:
        int: The task ID of the progress bar.
    """

    return progress.add_task(
        f"[pink]  {fpath}",
        total=filesize,
    )


async def _download_file(
    session: aiohttp.ClientSession,
    file: Dict,
    filedir: str,
    progress: Progress,
    task_id: TaskID,
    over_threshold: bool,
):

    # Get file metdata
    filename = file["dataFile"]["filename"]
    file_id = file["dataFile"]["id"]
    directory_label = file.get("directoryLabel", "")
    dv_path = os.path.join(directory_label, filename)

    if filedir:
        local_path = os.path.join(filedir, dv_path)
    else:
        local_path = dv_path

    url = f"/api/access/datafile/{file_id}"

    async with session.get(url) as response:
        response.raise_for_status()
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        async with aiofiles.open(local_path, "wb") as f:
            while True:
                chunk = await response.content.read(CHUNK_SIZE)
                progress.advance(task_id, advance=len(chunk))

                if over_threshold:
                    progress.update(task_id, visible=False)

                if not chunk:
                    break
                await f.write(chunk)

    return File(
        filepath=local_path,
        file_id=str(file_id),
        **file,
    )


def _filter_files(files: List[Dict], filenames: List[str]) -> List[Dict]:
    """Filters a list of files by filenames

    Args:
        files (List[Dict]): The list of files to filter.
        filenames (List[str]): The list of filenames to filter by.

    Returns:
        List[Dict]: The filtered list of files.
    """

    # Sort files by size
    files = sorted(files, key=lambda x: int(x["dataFile"]["filesize"]))

    if len(filenames) == 0:
        return files

    to_download = []

    for file in files:
        dv_path = os.path.join(
            file.get("directoryLabel", ""),
            file["dataFile"]["filename"],
        )

        if dv_path in filenames:
            to_download.append(file)

    return to_download
