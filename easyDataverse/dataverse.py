import asyncio
from copy import deepcopy
import json
from typing import Callable, Dict, List, Optional, Tuple, IO
from urllib import parse

import requests
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from anytree import Node, findall_by_attr
from dotted_dict import DottedDict
from pydantic import UUID4, BaseModel, ConfigDict, Field, HttpUrl, PrivateAttr
from pyDataverse.api import DataAccessApi, NativeApi
import rich

from .classgen import create_dataverse_class, remove_child_fields_from_global
from .connect import fetch_metadatablocks, gather_metadatablock_names
from .dataset import Dataset
from .downloader import download_files


class Dataverse(BaseModel):
    """
    Dataverse installation class to interact with an installation and
    provide basic dataset I/O functionalities and an interface to
    pyDataverse. This class offers the following functionalities:

    * Connect to a Dataverse installation
    * Create a blank dataset that complies to the metadatablocks of the Dataverse installation
    * Load a dataset from a DOI or URL (as a classmethod)

    Please note, that the Dataverse class is not compatible with the
    Dataverse versions <5.13 due to missing information to create
    the metadatablocks.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    server_url: HttpUrl = Field(
        ...,
        description="The URL of the Dataverse installation to connect to.",
    )

    api_token: Optional[UUID4] = Field(
        default=None,
        description="The API token to use for authentication. If not provided, only public data can be accessed.",
    )

    native_api: Optional[NativeApi] = Field(
        default=None,
        description="The native API provided by PyDataverse to use for interacting with the Dataverse installation beyond EasyDataverse.",
    )

    _dataset_gen: Callable = PrivateAttr(default=None)
    _connected: bool = PrivateAttr(default=False)

    def __init__(
        self,
        server_url: HttpUrl,
        api_token: Optional[UUID4] = None,
    ):
        super().__init__(
            server_url=server_url,
            api_token=api_token,
        )

        self._connect()
        self.native_api = NativeApi(
            base_url=str(self.server_url),
            api_token=str(self.api_token),  # type: ignore
        )

    def _connect(self) -> None:
        """Connects to a Dataverse installation and adds all metadtablocks as classes.

        You can access each of the given metadatablocks and
        fill these with your metadata by accessing via the
        common pythonic way to attributes. Here is an example:

        dataset.citation.title = "Title" -> Will set a title

        Sub-fields that are made of multiple arguments can either
        be accessed the same way as other fields (its just nested)
        or in the case of "multiple" be added via dedicated add-methods.

        dataset.citation.description(text="Description") -> Adds a decription

        Args:
            url (AnyHttpUrl): URL to the Dataverse installation

        Raises:
            requests.HTTPError: When the URL does not point to a valid DV

        Returns:
            Dataset: Object that contains all metadatablocks
        """

        if not self._version_is_compliant():
            raise ValueError(
                "The Dataverse installation is not compatible with easyDataverse. Please use a Dataverse installation >= 5.13.x"
            )

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        )

        print("\n")
        task = progress.add_task(f"Connecting to {str(self.server_url)}...", total=1)

        with progress:
            dataset = Dataset(
                API_TOKEN=str(self.api_token),
                DATAVERSE_URL=self.server_url,
            )

            block_names = gather_metadatablock_names(str(self.server_url))
            all_blocks = asyncio.run(
                fetch_metadatablocks(
                    block_names,
                    base_url=str(self.server_url),
                )
            )

            tasks = [
                self._process_metadatablock(dataset, block) for block in all_blocks
            ]
            asyncio.run(asyncio.gather(*tasks))  # type: ignore

            self._dataset_gen = lambda: deepcopy(dataset)
            self._connected = True

            progress.update(
                task,
                completed=1,
                visible=False,
            )

            rich.print(f"🎉 [bold]Connected to '{self.server_url}'[/bold]")

    async def _process_metadatablock(
        self,
        dataset: Dataset,
        block: Dict,
    ):
        """
        Process a metadata block for a dataset.

        Args:
            dataset (Dataset): The dataset object to which the metadata block belongs.
            block (Dict): The metadata block to process.

        """
        metadatablock = deepcopy(block)
        fields = remove_child_fields_from_global(metadatablock.data.fields)  # type: ignore
        primitives = list(
            filter(lambda field: "childFields" not in field, fields.values())
        )
        compounds = list(filter(lambda field: "childFields" in field, fields.values()))

        block_cls = create_dataverse_class(
            metadatablock.data.name, primitives, compounds  # type: ignore
        )
        block_cls._metadatablock_name = metadatablock.data.name  # type: ignore

        dataset.add_metadatablock(block_cls())

    def _version_is_compliant(self) -> bool:
        """Checks whether the Dataverse version is 5.13 or above.

        Returns:
            bool: True if the version is compliant, False otherwise.

        Raises:
            ValueError: If the server URL is not a valid Dataverse installation or version info is not found.
        """
        response = requests.get(
            parse.urljoin(str(self.server_url), "/api/info/version")
        )

        if response.status_code != 200:
            raise ValueError(
                f"URL '{self.server_url}' is not a valid Dataverse installation. Couldnt find version info."
            )

        major, minor, *_ = response.json()["data"]["version"].split(".")

        if int(major) >= 6:
            return True
        elif int(major) >= 5 and int(minor) >= 13:
            return True

        return False

    # ! Printers
    def list_metadatablocks(self, detailed: bool = False):
        """
        Lists the metadata blocks available in the connected Dataverse instance.

        Args:
            detailed (bool, optional): If True, provides detailed information about each metadata block.
                Defaults to False.

        Raises:
            AssertionError: If not connected to a Dataverse instance.

        Returns:
            None
        """
        assert (
            self._connected
        ), "Please connect to a Dataverse instance to list metadatablocks."

        self.create_dataset().list_metadatablocks(detailed=detailed)

    # ! Dataset Handlers

    def create_dataset(self) -> Dataset:
        """
        Creates a blank dataset that complies to the metadatablocks of the Dataverse installation.

        Returns:
            Dataset: The newly created dataset.
        """
        return self._dataset_gen()

    @classmethod
    def load_from_url(
        cls,
        url: str,
        api_token: Optional[str] = None,
        filedir: str = ".",
        download_files: bool = True,
        filenames: List[str] = [],
        n_parallel_downloads: int = 10,
    ) -> Tuple[Dataset, "Dataverse"]:
        """Fetches a dataset and Dataverse specific information from an URL.

        Using this method will allow you to retrieve a dataset from a Dataverse installation and
        simultaneously retrieve all information about the Dataverse installation itself to further
        modify or extend the dataset.

        Args:
            url (str): URL to the dataset
            api_token (Optional[str], optional): API token to use for authentication. Defaults to None.
            filedir (str, optional): Directory to store the files in. Defaults to ".".
            download_files (bool, optional): Whether to download the files or not. Defaults to True.
            filenames (Optional[List[str]], optional): List of filenames to download. Defaults to None.
            n_parallel_downloads (int, optional): Number of parallel downloads. Defaults to 10.

        Returns:
            Tuple[Dataset, Dataverse]: The dataset and the Dataverse installation.
        """

        # Extract parameters and server URL
        parsed_url = parse.urlparse(url)
        p_id = parse.parse_qs(parsed_url.query)["persistentId"][0]

        try:
            version = parse.parse_qs(parsed_url.query)["version"][0]
        except KeyError:
            version = "latest"

        server_url = parse.urlunparse(
            (parsed_url.scheme, parsed_url.netloc, "", "", "", "")
        )

        # Instantiate and load the dataset
        dataverse = cls(server_url, api_token)  # type: ignore
        dataset = dataverse.load_dataset(
            pid=p_id,
            version=version,
            filedir=filedir,
            download_files=download_files,
            filenames=filenames,
            n_parallel_downloads=n_parallel_downloads,
        )

        return dataset, dataverse

    def load_dataset(
        self,
        pid: str,
        version: str = "latest",
        filedir: str = ".",
        filenames: List[str] = [],
        download_files: bool = True,
        n_parallel_downloads: int = 10,
    ) -> Dataset:
        """Retrieves dataset from DOI if connected to an installation as a Dataset object.

        Args:
            pid (str): Persistent identifier of the dataset.
            version (str, optional): Version of the dataset. Defaults to "latest".
            filedir (str, optional): Directory to store the files in. Defaults to ".".
            filenames (Optional[List[str]], optional): List of filenames to download. Defaults to None.
            download_files (bool, optional): Whether to download the files or not. Defaults to True.

        Returns:
            Dataset: The dataset.
        """

        rich.print(f"[bold]Fetching dataset '{pid}' from '{self.server_url}'[/bold]\n")

        # Create a blank dataset
        dataset = self.create_dataset()

        # Fetch and extract data
        remote_ds = self._fetch_dataset(pid, version)
        dataset.p_id = remote_ds.data.latestVersion.datasetPersistentId  # type: ignore
        blocks = remote_ds.data.latestVersion.metadataBlocks  # type: ignore
        files = remote_ds.data.latestVersion.files  # type: ignore

        # Process metadatablocks and files
        self._construct_block_classes(blocks, dataset)

        info = "\n".join(
            [
                f"Title: [bold]{dataset.citation.title}[/bold]",  # type: ignore
                f"Version: {version}",
                f"Files: {len(files)}",
            ]
        )

        panel = Panel(
            info,
            title="[bold]Dataset Information[/bold]",
            expand=False,
        )

        rich.print(panel)

        if download_files:
            self._fetch_files(
                dataset=dataset,
                files_list=files,  # type: ignore
                filedir=filedir,
                filenames=filenames,
                n_parallel_downloads=n_parallel_downloads,
            )

        return dataset

    def _fetch_dataset(
        self,
        pid: str,
        version: str,
    ) -> Dict:
        """Fetches a specific dataset version by its persistent identifier."""

        if version == "DRAFT":
            version = "latest"

        endpoint = f"/api/datasets/:persistentId/?persistentId={pid}"
        url = parse.urljoin(
            str(self.server_url),
            endpoint,
        )  # type: ignore
        header = {}

        if self.api_token is not None:
            header["X-Dataverse-key"] = str(self.api_token)

        if version != "latest":
            return self._fetch_dataset_version(pid, str(version))

        return DottedDict(requests.get(url, headers=header).json())

    def _fetch_files(
        self,
        dataset: Dataset,
        files_list: List[Dict],
        filedir: str,
        filenames: List[str],
        n_parallel_downloads: int,
    ):
        """Fetches all files of a dataset."""

        if self.api_token:
            data_api = DataAccessApi(
                str(self.server_url),
                str(self.api_token),
            )
        else:
            data_api = DataAccessApi(str(self.server_url))

        if len(files_list) == 0:
            return

        files = asyncio.run(
            download_files(
                data_api=data_api,
                files_list=files_list,
                filedir=filedir,
                filenames=filenames,
                n_parallel_downloads=n_parallel_downloads,
            )
        )

        dataset.files += files

    def _construct_block_classes(
        self,
        blocks: Dict,
        dataset: Dataset,
    ) -> None:
        """Parse the blocks and create the corresponding classes."""

        for name, block in blocks.items():
            metadatablock = dataset.metadatablocks[name]

            tree = metadatablock._create_tree()
            content = self._extract_data(block.fields, tree)

            dataset.metadatablocks[name] = metadatablock.__class__.parse_obj(content)
            setattr(dataset, name, dataset.metadatablocks[name])

    def _fetch_dataset_version(
        self,
        dataset_pid: str,
        version: str,
    ) -> Dict:
        """
        Fetches a specific dataset version by first fetching all versions
        and then extracting the desired one. Given it exists.
        """

        # Fetch all versions
        versions = self._available_versions(dataset_pid)

        if version not in versions:
            raise ValueError(
                f"Version {version} not found. These are the available versions: {versions.keys()}"
            )

        return DottedDict({"data": {"latestVersion": versions[version]}})

    def _available_versions(
        self,
        dataset_pid: str,
    ) -> Dict[str, Dict]:
        """Fetches all available versions of a dataset.

        Args:
            dataset_pid (str): Persistent identifier of the dataset.
            api (NativeApi): API object to use for the request.

        Returns:
            Dict[str, Dict]: Mapping of version number to dataset metadata.
        """

        assert (
            self.native_api is not None
        ), "Native API is not available. Please connect to a Dataverse installation first."

        response = self.native_api.get_dataset_versions(dataset_pid)

        if response.status_code != 200:
            raise Exception(f"Error getting dataset versions: {response.text}")

        return {
            str(dataset["versionNumber"]): dataset
            for dataset in response.json()["data"]
            if dataset["versionState"] != "DRAFT"
        }

    def _extract_data(self, fields: List, tree: Node):
        """
        Extracts data from a metadatablock that has been fetched as a
        dataset from a Dataverse installation.
        """

        if all(not isinstance(entry, dict) for entry in fields):
            return fields

        data = {}

        for field in fields:
            node = findall_by_attr(tree, field.typeName, "typeName")[0]
            name = node.name
            dvtype = node.typeClass

            if dvtype.lower() == "compound":
                data[name] = self._process_compound(field.value, tree)
            else:
                data[name] = field.value

        return data

    def _process_compound(self, compound, tree):
        """Processes given field value according to its 'multiple' state"""

        if isinstance(compound, list):
            return [
                self._extract_data(list(entry.values()), tree) for entry in compound
            ]

        return self._extract_data(compound, tree)

    # ! Importers
    def dataset_from_json(self, handler: IO) -> Dataset:
        """
        Creates a dataset object from a JSON file.

        Args:
            handler (IO): The file handler for the JSON file.

        Returns:
            Dataset: The created dataset object.

        Raises:
            AssertionError: If the Dataverse installation is not connected or if the file does not exist.
        """

        assert self._connected, "Please connect to a Dataverse installation first."

        dataset = self.create_dataset()
        data = json.load(handler)

        # Map metadatablocks to dataset
        self._map_blocks_to_dataset(dataset, data)

        return dataset

    def dataset_from_json_string(self, json_string: str) -> Dataset:
        """
        Creates a dataset object from a JSON string representation.

        Args:
            json_string (str): The JSON string representation of the dataset.

        Returns:
            Dataset: The dataset object created from the JSON string.
        """

        assert self._connected, "Please connect to a Dataverse installation first."

        dataset = self.create_dataset()
        data = json.loads(json_string)

        # Map metadatablocks to dataset
        self._map_blocks_to_dataset(dataset, data)

        return dataset

    def _map_blocks_to_dataset(self, dataset: Dataset, data: Dict) -> None:
        """
        Maps the metadatablocks to the dataset object.

        Args:
            dataset (Dataset): The dataset object to map the metadatablocks to.
            data (Dict): The dictionary containing the metadatablocks.

        Returns:
            None
        """

        assert "metadatablocks" in data, "No metadatablocks found in JSON."
        assert isinstance(
            data["metadatablocks"], dict
        ), "Metadatablocks must be a dictionary."

        for name, content in data["metadatablocks"].items():
            if not hasattr(dataset, name):
                rich.print(
                    f"[bold red]Warning:[/bold red] Metadatablock '{name}' not available at '{self.server_url}'."
                )

            block = getattr(dataset, name)
            dataset.metadatablocks[name] = block.__class__(**content)
            setattr(
                dataset,
                name,
                dataset.metadatablocks[name],
            )
