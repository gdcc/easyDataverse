import grequests
import requests

from copy import deepcopy
from typing import Callable, Dict, List, Optional, Tuple
from urllib import parse

from anytree import Node, findall_by_attr
from dotted_dict import DottedDict
from pydantic import BaseModel, Field, PrivateAttr, HttpUrl, UUID4
from pyDataverse.api import NativeApi, DataAccessApi

from .utils import download_files
from .dataset import Dataset
from .connect import (
    create_dataverse_class,
    fetch_metadatablocks,
    remove_child_fields_from_global,
)


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

    class Config:
        arbitrary_types_allowed = True

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

        print(f"Connecting to {self.server_url}")

        if not self._version_is_compliant():
            raise ValueError(
                "The Dataverse installation is not compatible with easyDataverse. Please use a Dataverse installation >= 5.13.x"
            )

        dataset = Dataset(API_TOKEN=str(self.api_token), DATAVERSE_URL=self.server_url)
        all_blocks = fetch_metadatablocks(self.server_url)

        for metadatablock in all_blocks.values():
            metadatablock = deepcopy(metadatablock)
            fields = remove_child_fields_from_global(metadatablock.data.fields)
            primitives = list(
                filter(lambda field: "childFields" not in field, fields.values())
            )
            compounds = list(
                filter(lambda field: "childFields" in field, fields.values())
            )

            block_cls = create_dataverse_class(
                metadatablock.data.name, primitives, compounds
            )
            block_cls._metadatablock_name = metadatablock.data.name

            dataset.add_metadatablock(block_cls())

        self._dataset_gen = lambda: deepcopy(dataset)

        print("Connection successfuly established!")

    def _version_is_compliant(self) -> bool:
        """Checks whether the Dataverse version is 5.13 or above."""
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

    # ! Dataset Handlers

    def create_dataset(self) -> Dataset:
        """Creates a blank dataset that complies to the metadatablocks of the Dataverse installation."""
        return self._dataset_gen()

    @classmethod
    def load_from_url(
        cls,
        url: str,
        api_token: Optional[str] = None,
        filedir: str = ".",
        download_files: bool = True,
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

        Returns:
            Tuple[Dataset, Dataverse]: The dataset and the Dataverse installation.
        """

        # Extract parameters and server URL
        parsed_url = parse.urlparse(url)
        p_id = parse.parse_qs(parsed_url.query)["persistentId"][0]
        version = parse.parse_qs(parsed_url.query)["version"][0]
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
        )

        return dataset, dataverse

    def load_dataset(
        self,
        pid: str,
        version: str = "latest",
        filedir: str = ".",
        filenames: Optional[List[str]] = None,
        download_files: bool = True,
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

        # Create a blank dataset
        dataset = self.create_dataset()

        # Fetch and extract data
        remote_ds = self._fetch_dataset(pid, version)
        dataset.p_id = remote_ds.data.latestVersion.datasetPersistentId  # type: ignore
        blocks = remote_ds.data.latestVersion.metadataBlocks  # type: ignore

        # Process metadatablocks and files
        self._construct_block_classes(blocks, dataset)

        if download_files:
            self._fetch_files(
                dataset,
                remote_ds.data.latestVersion.files,  # type: ignore
                filedir,
                filenames,
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
        url = parse.urljoin(self.server_url, endpoint)
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
        filenames: Optional[List[str]] = None,
    ):
        """Fetches all files of a dataset."""

        if self.api_token:
            data_api = DataAccessApi(self.server_url, str(self.api_token))
        else:
            data_api = DataAccessApi(self.server_url)

        download_files(
            data_api,
            dataset,
            files_list,
            filedir,
            filenames,
        )

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