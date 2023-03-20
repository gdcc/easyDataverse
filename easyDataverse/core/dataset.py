import deepdish as dd
import json
import os
import warnings
import xmltodict
import yaml
import requests

from copy import deepcopy
from pydantic import BaseModel, validate_arguments, Field, AnyHttpUrl
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs
from json import dumps
from anytree import Node, findall_by_attr
from dotted_dict import DottedDict
from urllib.parse import urljoin

from easyDataverse.core.file import File
from easyDataverse.core.exceptions import MissingCredentialsException
from easyDataverse.core.base import DataverseBase
from easyDataverse.tools.uploader.uploader import upload_to_dataverse, update_dataset
from easyDataverse.tools.software.softwareinfo import ProgrammingLanguage
from easyDataverse.tools.software.softwaretools import dataset_from_repository
from easyDataverse.tools.utils import YAMLDumper, get_class
from easyDataverse.tools.connect.connect import (
    fetch_metadatablocks,
    remove_child_fields_from_global,
    create_dataverse_class,
)
from easyDataverse.tools.downloader.downloader import (
    download_from_dataverse_with_lib,
    download_from_dataverse_without_lib,
)


class Dataset(BaseModel):
    class Config:
        extra = "allow"

    metadatablocks: Dict[str, Any] = dict()
    p_id: Optional[str] = None
    files: List[File] = Field(default_factory=list)
    API_TOKEN: Optional[str] = Field(None)
    DATAVERSE_URL: Optional[str] = Field(None)

    # ! Adders
    def add_metadatablock(self, metadatablock: DataverseBase) -> None:
        """Adds a metadatablock object to the dataset if it is of 'DataverseBase' type and has a metadatablock name"""

        # Check if the metadatablock is of 'DataverseBase' type
        if issubclass(metadatablock.__class__, DataverseBase) is False:
            raise TypeError(
                f"Expected class of type 'DataverseBase', got '{metadatablock.__class__.__name__}'"
            )

        if hasattr(metadatablock, "_metadatablock_name") is False:

            raise TypeError(
                f"The provided class {metadatablock.__class__.__name__} has no metadatablock name and is thus not compatible with this function."
            )

        # Add the metadatablock to the dataset as a dict
        block_name = getattr(metadatablock, "_metadatablock_name")
        self.metadatablocks.update({block_name: metadatablock})

        # ... and to the __dict__
        setattr(self, block_name, metadatablock)

    def add_file(self, local_path: str, dv_dir: str = "", description: str = ""):
        """Adds a file to the dataset based on the provided path.

        Args:
            filename (str): Path to the file to be added.
            description (str, optional): Description of the file. Defaults to "".
        """

        # Create the file
        filename = os.path.basename(local_path)
        file = File(
            filename=filename,
            dv_dir=dv_dir,
            local_path=local_path,
            description=description,
        )

        if file not in self.files:
            self.files.append(file)
        else:
            raise FileExistsError(f"File has already been added to the dataset")

    def add_directory(
        self,
        dirpath: str,
        dv_dir: str = "",
        include_hidden: bool = False,
        ignores: List[str] = [],
    ) -> None:
        """Adds an entire directory including subdirectories to Dataverse.

        Args:
            dirpath (str): Path to the directory
            include_hidden (bool, optional): Whether or not hidden folders "." should be included. Defaults to False.
            ignores (List[str], optional): List of extensions/directories that should be ignored. Defaults to [].

        """

        dirpath = os.path.join(dirpath)

        if not os.path.isdir(dirpath):
            raise FileNotFoundError(
                f"Directory at {dirpath} does not exist or is not a directory. Please provide a valid directory."
            )

        for path, _, files in os.walk(dirpath):

            if self._has_hidden_dir(path, dirpath) and not include_hidden:
                # Checks whether the current path from the
                # directory tree contains any hidden dirs
                continue

            if self._has_ignore_dirs(path, dirpath, ignores):
                # Checks whether the directory or file is in the
                # list of ignored data
                continue

            for file in files:
                if file.startswith("."):
                    # Skip hidden files
                    continue

                # Get all the metadata
                filepath = os.path.join(path, file)

                path_parts = [
                    p
                    for p in filepath.split(os.path.sep)
                    if not p in dirpath.split(os.path.sep)
                ]
                filename = os.path.join(*path_parts)

                if dirpath != ".":
                    # Just catch the structure inside the dir
                    dv_pre = os.path.join(
                        dv_dir, os.path.dirname(filepath.split(dirpath)[-1])
                    )
                else:
                    dv_pre = dv_dir

                data_file = File(filename=filename, local_path=filepath, dv_dir=dv_pre)

                # Substitute new files with old files
                found = False
                for f in self.files:
                    if f.filename == filename:
                        f.local_path = data_file.local_path
                        found = True
                        break

                if not found:
                    self.files.append(data_file)

    @staticmethod
    def _has_hidden_dir(path: str, dirpath: str) -> bool:
        """Checks whether a hidden directory ('.') exists in a path."""

        if path == dirpath:
            # For the case of a '.' as dirpath
            return False

        path = path.replace(f"{dirpath}{os.sep}", "")
        dirs = os.path.normpath(path).split(os.sep)
        return any(dir.startswith(".") for dir in dirs)

    @staticmethod
    def _has_ignore_dirs(path: str, dirpath: str, ignores: List[str]) -> bool:
        """Checks whether there are directories that should be ignored"""
        path = path.replace(f"{dirpath}{os.sep}", "")
        dirs = os.path.normpath(path).split(os.sep)

        check = []
        for ignore in ignores:
            for dir in dirs:
                if len(ignore) > 0:
                    check.append(ignore.replace("/", "") in dir)

        return any(check)

    # ! Exporters

    def xml(self) -> str:
        """Returns an XML representation of the dataverse object."""

        # Turn all keys to be camelcase
        fields = self._keys_to_camel({"dataset_version": self.dict()})

        return xmltodict.unparse(fields, pretty=True, indent="    ")

    def dataverse_dict(self) -> dict:
        """Returns a dictionary representation of the dataverse dataset."""

        # Convert all blocks to the appropriate format
        blocks = {}
        for block in self.metadatablocks.values():
            blocks.update(block.dataverse_dict())

        return {"datasetVersion": {"metadataBlocks": blocks}}

    def dataverse_json(self, indent: int = 2) -> str:
        """Returns a JSON representation of the dataverse dataset."""

        return dumps(self.dataverse_dict(), indent=indent)

    def dict(self, **kwargs):
        """Builds the basis of exports towards other formats."""

        data = {"metadatablocks": {}}

        if self.p_id:
            data["dataset_id"] = self.p_id

        for name, block in self.metadatablocks.items():
            block = block.dict(exclude_none=True)

            if block != {}:
                data["metadatablocks"][name] = block

        return data

    def yaml(self) -> str:
        """Exports the dataset as a YAML file that can also be read by the API"""

        # Get the name of the module to ensure
        # that the correct one is used when reading
        # the YAML file later on

        return yaml.dump(
            self.dict(), Dumper=YAMLDumper, default_flow_style=False, sort_keys=False
        )

    def json(self) -> str:
        """Exports the dataset as a JSON file that can also be read by the API"""
        return json.dumps(self.dict(), indent=4)

    def hdf5(self, path: str) -> None:
        """Exports the dataset to an HDF5 dataset that can also be read by the API

        Args:
            path (str): Path to the destination HDF5 files.
        """

        # Write metatdat to hdf5
        dd.io.save(path, self.dict(exclude={"files"}, exclude_none=True))

    # ! Dataverse interfaces

    def upload(
        self,
        dataverse_name: str,
        content_loc: Optional[str] = None,
    ) -> str:
        """Uploads a given dataset to a Dataverse installation specified in the environment variable.

        Args:
            dataverse_name (str): Name of the target dataverse.
            filenames (List[str], optional): File or directory names which will be uploaded. Defaults to None.
            content_loc (Optional[str], optional): If specified, the ZIP that is used to upload will be stored at the destination provided. Defaults to None.
        Returns:
            str: [description]
        """

        self.p_id = upload_to_dataverse(
            json_data=self.dataverse_json(),
            dataverse_name=dataverse_name,
            files=self.files,
            p_id=self.p_id,
            DATAVERSE_URL=self.DATAVERSE_URL,
            API_TOKEN=self.API_TOKEN,
            content_loc=content_loc,
        )

        return self.p_id

    def update(
        self,
        contact_name: Optional[str] = None,
        contact_mail: Optional[str] = None,
        content_loc: Optional[str] = None,
    ):
        """Updates a given dataset if a p_id has been given.

        Use this function in conjunction with 'from_dataverse_doi' to edit and update datasets.
        Due to the Dataverse REST API, downloaded datasets wont include contact mails, but in
        order to update the dataset it is required. For this, provide a name and mail for contact.
        EasyDataverse will search existing contacts and when a name fits, it will add the mail.
        Otherwise a new contact is added to the dataset.

        Args:
            contact_name (str, optional): Name of the contact. Defaults to None.
            contact_mail (str, optional): Mail of the contact. Defaults to None.
            content_loc (Optional[str], optional): If specified, the ZIP that is used to upload will be stored at the destination provided. Defaults to None.
        """

        # Update contact
        # if contact_name is None and contact_mail is None:
        #     # Check if there is already a contact defined
        #     contact_mails = [
        #         contact.email for contact in self.citation.contact if contact.email
        #     ]

        #     if len(contact_mails) == 0:
        #         raise ValueError(
        #             f"Please provide a contact name and email to update the dataset"
        #         )

        # Check if there is a contact with the given name already in the dataset
        has_mail = False
        # for contact in self.citation.point_of_contact:
        #     if contact.name == contact_name:
        #         contact.email = contact_mail
        #         has_mail = True

        # if has_mail == False:
        #     # Assign a completely new contact if the name is new
        #     self.citation.add_contact(name=contact_name, email=contact_mail)

        update_dataset(
            json_data=self.dataverse_dict()["datasetVersion"],
            p_id=self.p_id,
            files=self.files,
            DATAVERSE_URL=self.DATAVERSE_URL,
            API_TOKEN=self.API_TOKEN,
            content_loc=content_loc,
        )

    # ! Initializers
    @classmethod
    def connect(cls, url: AnyHttpUrl, API_TOKEN: Optional[str] = None) -> "Dataset":
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

        dataset = cls()
        all_blocks = fetch_metadatablocks(url)

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

        dataset.DATAVERSE_URL = url
        dataset.API_TOKEN = API_TOKEN

        return dataset

    @classmethod
    @validate_arguments
    def from_url(
        cls,
        url: str,
        filedir: str = ".",
        download_files: bool = True,
        api_token: Optional[str] = None,
        lib_name: Optional[str] = None,
    ):
        # Break down the URL and gather doi and target url
        # Example: https://darus.uni-stuttgart.de/dataset.xhtml?persistentId=doi:10.18419/darus-2469

        parsed_url = urlparse(url)
        doi = parse_qs(parsed_url.query).get("persistentId")

        if doi is None:
            raise ValueError(
                f"Given URL '{url}' is not a valid Dataverse URL since no 'persistenID' is given"
            )

        dataverse_url = f"https://{parsed_url.hostname}/"

        return cls.from_dataverse_doi(
            doi=doi[0],
            filedir=filedir,
            lib_name=lib_name,
            dataverse_url=dataverse_url,
            api_token=api_token,
            download_files=download_files,
        )

    def from_doi(self, doi: str):
        """Retrieves dataset from DOI if connected to an installation"""

        fetch_path = f"/api/datasets/:persistentId/?persistentId={doi}"
        fetch_url = urljoin(self.DATAVERSE_URL, fetch_path)

        header = {"X-Dataverse-key": self.API_TOKEN}

        remote_ds = DottedDict(requests.get(fetch_url, headers=header).json())
        self.p_id = remote_ds.data.latestVersion.datasetPersistentId
        blocks = remote_ds.data.latestVersion.metadataBlocks

        for name, block in blocks.items():
            metadatablock = self.metadatablocks[name]

            tree = metadatablock._create_tree()
            content = self.extract_data(block.fields, tree)

            self.metadatablocks[name] = metadatablock.__class__.parse_obj(content)
            setattr(self, name, self.metadatablocks[name])

        return self

    def extract_data(self, fields: List, tree: Node):
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
                data[name] = self.process_compound(field.value, tree)
            else:
                data[name] = field.value

        return data

    def process_compound(self, compound, tree):
        """Processes give field value according to its 'multiple' state"""

        if isinstance(compound, list):
            return [self.extract_data(list(entry.values()), tree) for entry in compound]

        return self.extract_data(compound)

    @classmethod
    @validate_arguments
    def from_dataverse_doi(
        cls,
        doi: str,
        filedir: Optional[str] = ".",
        filenames: Optional[List[str]] = None,
        download_files: bool = True,
        lib_name: Optional[str] = None,
        dataverse_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        """Initializes a Dataset from a given Dataverse dataset.

        Args:
            doi (str): DOI of the dataverse Dataset.
            filedir (str): Path to the directory where files will be downloaded to.
            download_files (bool): Whether or not files should be downloaded. Will override 'filedir'
            lib_name (str, optional): Name of the library to fetch the given metadatablocks.

        Returns:
            Dataset: Resulting dataset that has been downloaded from Dataverse.
        """

        if download_files is False:
            filedir = None

        if not doi.startswith("doi:"):
            doi = f"doi:{doi}"

        # Get credentials
        url, api_token = cls._fetch_env_vars(api_token)

        if url is None and dataverse_url is None:
            raise ValueError(
                "".join(
                    [
                        "Dataverse URL has not been specified explicitly or in the environment variables as 'DATAVERSE_URL'. ",
                        "Please specify it to download datasets from your desired installation.",
                    ]
                )
            )

        if not lib_name and "EASYDATAVERSE_LIB_NAME" not in os.environ:
            if not dataverse_url:
                raise ValueError(
                    "Dataverse URL has not been specified in argument 'dataverse_url'. Please specify it to download datasets from your desired installation."
                )
            return cls._fetch_without_lib(
                dataset=cls(),
                doi=doi,
                filedir=filedir,
                dataverse_url=dataverse_url,
                api_token=api_token,
                filenames=filenames,
            )

        elif not lib_name and "EASYDATAVERSE_LIB_NAME" in os.environ:
            dataverse_url, api_token = cls._fetch_env_vars(api_token)
            lib_name = os.environ["EASYDATAVERSE_LIB_NAME"]
            return cls._fetch_with_lib(
                dataset=cls(),
                doi=doi,
                lib_name=lib_name,
                filedir=filedir,
                dataverse_url=url,
                api_token=api_token,
                filenames=filenames,
            )
        else:
            dataverse_url, api_token = cls._fetch_env_vars()
            return cls._fetch_with_lib(
                dataset=cls(),
                doi=doi,
                lib_name=lib_name,
                filedir=filedir,
                dataverse_url=url,
                api_token=api_token,
                filenames=filenames,
            )

    @staticmethod
    def _fetch_env_vars(api_token: Optional[str] = None):
        """Fetches DATAVERSE_URL and DATAVERSE_API_TOKEN from environment variables"""

        if api_token is None:
            return os.environ.get("DATAVERSE_URL"), os.environ.get(
                "DATAVERSE_API_TOKEN"
            )
        else:
            return os.environ.get("DATAVERSE_URL"), api_token

    @staticmethod
    def _fetch_without_lib(**kwargs):
        """Fetches the dataset without using a dedicated library."""

        if not kwargs.get("api_token"):
            # Infer API_TOKEN from environment if not explicitly specified.
            try:
                kwargs["api_token"] = os.environ["DATAVERSE_API_TOKEN"]
            except KeyError:
                warnings.warn(
                    "No 'API_TOKEN' found in the environment. Please be aware, that you might not have the rights to download this dataset."
                )

        return download_from_dataverse_without_lib(**kwargs)

    @staticmethod
    def _fetch_with_lib(**kwargs):
        """Fetches the dataset with a dedicated library."""
        return download_from_dataverse_with_lib(**kwargs)

    @classmethod
    def from_json(cls, path: str, use_id: bool = True):
        """Initializes a dataset based on a given YAML file.

        The specifications for the JSON file include the following:
        {
            lib_name: "Important to infer the metadatablocks. For instance 'pyDaRUS'.",
            dataset_id: "Used to update datasets that are already given. Leave out for new ones.",
            metadatablocks: {
                block1: {
                    field1: Content of the field
                    field2: ...
                },
                block2: {
                    field1: ...
                }
            }
        }

        Args:
            path (str): Path to the YAML file.
            use_id (bool): Whether or not the Dataset ID should be included. Defaults to True.

        Returns:
            Dataset: The resulting Dataset instance.
        """

        # Load JSON file
        with open(path, "r") as file_handle:
            data = json.loads(file_handle.read())

        return cls.from_dict(data, use_id)

    @classmethod
    def from_yaml(cls, path: str, use_id: bool = True):
        """Initializes a dataset based on a given YAML file.

        The specifications for the YAML file include the following:

        lib_name: Important to infer the metadatablocks. For instance 'pyDaRUS'.
        dataset_id: Used to update datasets that are already given. Leave out for new ones.
        metadatablocks:
          block1:
           field1: Content of the field
           field2: ...
          blocks2:
           field1: ...

        Args:
            path (str): Path to the YAML file.
            use_id (bool): Whether or not the Dataset ID should be included. Defaults to True.

        Returns:
            Dataset: The resulting Dataset instance.
        """

        # Load YAML file
        with open(path, "r") as file_handle:
            data = yaml.safe_load(file_handle.read())

        return cls.from_dict(data, use_id)

    @classmethod
    def from_dict(cls, data: dict, use_id: bool = True):

        # Initialize blank dataset
        # and get lib_name for imports
        dataset = cls()
        lib_name = data["lib_name"]
        dataset_id = data.get("dataset_id")

        if dataset_id and use_id:
            # Assign ID if given
            dataset.p_id = dataset_id

        # Iteratively import the modules and add blocks
        for module_name, fields in data["metadatablocks"].items():

            # Adapt module name to the namespace of generated code
            module_name = f".metadatablocks.{module_name}"

            # Retrieve class and initialize using the given
            # YAML data as a dicitonary
            cls = get_class(module_name, lib_name)[-1]
            instance = cls(**fields)

            dataset.add_metadatablock(instance)

        return dataset

    @classmethod
    def from_local_repository(
        cls,
        programming_language: Optional[ProgrammingLanguage] = None,
        lib_name: Optional[str] = None,
        path: str = ".",
    ):
        """Initialiazes a Dataset object from a repository structure.

        This method will parse the contents of a repository given the standards
        of the provided programming langugae. For example, when a Python library
        is given, the setup.py/pyproject.toml/requirements.txt files will be
        parsed and appropriately mapped to the metadatablocks 'Citation' and
        'CodeMeta'.

        Args:
            programming_language (ProgrammingLanguage): Programming language that is used
            lib_name (str): Library used to create the dataset.
            path (str): Path to the repository. Defaults to current directory '.'.
            write_yaml (bool): Whether or not a '.dataverse' file will be written that contains the metadata.
        """

        # Set up dataset and add blocks
        dataset = cls()

        # Gather relevant metadatablocks
        if programming_language:
            citation, codemeta = dataset_from_repository(programming_language, lib_name)
            dataset.add_metadatablock(citation)
            dataset.add_metadatablock(codemeta)

        # Get all extensions to ignore from gitignore
        if os.path.exists("./.gitignore"):
            ignore = [
                line.strip().replace("*", "")
                for line in open("./.gitignore").readlines()
                if not line.startswith("#") and len(line) > 0
            ]
        else:
            ignore = []

        dataset.add_directory(path, ignores=ignore, include_hidden=False)

        return dataset

    # ! Utilities
    def list_metadatablocks(self):
        """Lists all metadatablocks present in this dataset instance"""

        for block in self.metadatablocks.values():
            print(block._metadatablock_name)

    def list_files(self):
        """Lists all files present in the dataset for inspection"""
        for file in self.files:
            print(f"{file.file_pid}\t{file.filename}")

    def replace_file(self, filename: str, local_path: str):
        """Replaces a given file which will be uploaded upon calling the 'update'-method

        Please note, this function is best used when replacing big files when the sole
        purpose is to update a file without downloading it. Hence, this method is best
        used in conjunction with the 'from_dataverse_doi' or 'from_url' method with
        'download_files' set to 'False'.
        """

        file = list(filter(lambda f: f.filename == filename, self.files))

        if len(file) == 0:
            raise ValueError(
                f"File '{filename}' is not present in the dataset. Please use 'list_files' to see which files are registered."
            )
        elif len(file) > 1:
            raise ValueError(
                "More than one file found under filename '{filename}'. This is actually impossible, but better to have an exception for the exception :-)"
            )

        file[0].local_path = local_path

    @staticmethod
    def _snake_to_camel(word: str) -> str:
        return "".join(x.capitalize() or "_" for x in word.split("_"))

    def _keys_to_camel(self, dictionary: dict):
        nu_dict = {}
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):
                nu_dict[self._snake_to_camel(key)] = self._keys_to_camel(
                    dictionary[key]
                )
            else:
                nu_dict[self._snake_to_camel(key)] = dictionary[key]
        return nu_dict
