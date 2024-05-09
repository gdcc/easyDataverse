import json
import os
from json import dumps
from typing import Dict, List, Optional

import nob
import xmltodict
import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from dvuploader import File, add_directory

from easyDataverse.base import DataverseBase
from easyDataverse.uploader import update_dataset, upload_to_dataverse
from easyDataverse.utils import YAMLDumper

# These may be inferred from the collection
# in the future, but for now the basic fields
# are required.
REQUIRED_FIELDS = [
    "citation/title",
    "citation/author/authorName",
    "citation/datasetContact/datasetContactName",
    "citation/datasetContact/datasetContactEmail",
    "citation/dsDescription/dsDescriptionValue",
    "citation/subject",
]


class Dataset(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )

    metadatablocks: Dict[str, DataverseBase] = dict()
    p_id: Optional[str] = None
    files: List[File] = Field(default_factory=list)

    API_TOKEN: Optional[str] = Field(None)
    DATAVERSE_URL: Optional[HttpUrl] = Field(None)

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

    def add_file(
        self,
        local_path: str,
        dv_dir: str = "",
        categories: List[str] = ["DATA"],
        description: str = "",
    ):
        """Adds a file to the dataset based on the provided path.

        Args:
            local_path (str): Path to the file.
            dv_dir (str, optional): Directory in which the file should be stored in Dataverse. Defaults to "".
            categories (List[str], optional): List of categories to assign to the file. Defaults to ["DATA"].
            description (str, optional): Description of the file. Defaults to "".

        Raises:
            FileExistsError: If the file has already been added to the dataset.
        """

        file = File(
            filepath=local_path,
            directoryLabel=dv_dir,
            description=description,
            categories=categories,
        )

        if file not in self.files:
            self.files.append(file)
        else:
            raise FileExistsError(f"File has already been added to the dataset")

    def add_directory(
        self,
        dirpath: str,
        dv_dir: str = "",
        ignores: List[str] = [r"^\."],
    ) -> None:
        """Adds an entire directory including subdirectories to Dataverse.

        Args:
            dirpath (str): Path to the directory
            include_hidden (bool, optional): Whether or not hidden folders "." should be included. Defaults to False.
            ignores (List[str], optional): List of extensions/directories that should be ignored. Defaults to [].
        """

        self.files += add_directory(
            directory=dirpath,
            directory_label=dv_dir,
            ignore=ignores,
        )

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

        return dumps(self.dataverse_dict(), indent=indent, default=str)

    def dict(self, exclude_none: bool = True, **kwargs):
        """Builds the basis of exports towards other formats."""

        data = {"metadatablocks": {}}

        if self.p_id:
            data["dataset_id"] = self.p_id  # type: ignore

        for name, block in self.metadatablocks.items():
            block = block.dict(exclude_none=exclude_none)

            if block != {}:
                data["metadatablocks"][name] = block

        return data

    def yaml(self, exclude_none: bool = True) -> str:
        """Exports the dataset as a YAML file that can also be read by the API"""
        return yaml.dump(
            self.dict(exclude_none=exclude_none),
            Dumper=YAMLDumper,
            default_flow_style=False,
            sort_keys=False,
        )

    def json(self) -> str:
        """Exports the dataset as a JSON file that can also be read by the API"""
        return json.dumps(self.dict(), indent=4, default=str)

    # ! Dataverse interfaces
    def upload(
        self,
        dataverse_name: str,
        n_parallel: int = 1,
    ) -> str:
        """Uploads a given dataset to a Dataverse installation specified in the environment variable.

        Args:
            dataverse_name (str): Name of the target dataverse.
            n_parallel (int, optional): Number of parallel uploads to perform. Defaults to 1.

        Returns:
            str: The identifier of the uploaded dataset.
        """

        self._validate_required_fields()

        self.p_id = upload_to_dataverse(
            json_data=self.dataverse_json(),
            dataverse_name=dataverse_name,
            files=self.files,
            p_id=self.p_id,
            DATAVERSE_URL=str(self.DATAVERSE_URL),
            API_TOKEN=str(self.API_TOKEN),
            n_parallel=n_parallel,
        )

        return self.p_id

    def update(self):
        """Updates a dataset if a p_id has been given.

        Use this function to update a dataset that has already been uploaded to Dataverse.
        """

        if not self.p_id:
            raise ValueError("No dataset identifier has been given.")

        update_dataset(
            to_change=self._extract_changes(),
            p_id=self.p_id,  # type: ignore
            files=self.files,
            DATAVERSE_URL=str(self.DATAVERSE_URL),  # type: ignore
            API_TOKEN=str(self.API_TOKEN),
        )

    def _extract_changes(self) -> Dict:
        """Extracts the changes that have been made to the dataset."""

        changes = []
        for block in self.metadatablocks.values():
            changes += block.extract_changed()

        return {"fields": changes}

    # ! Validation
    def _validate_required_fields(self):
        """Validates whether all required fields are present and not empty.

        Raises:
            ValueError: If a required field is not present or empty.
        """

        results = []

        for field in REQUIRED_FIELDS:
            results.append(self._validate_required_field(field))

        assert all(
            result for result in results
        ), "Required fields are missing or empty. Please provide a value for these fields."

    def _validate_required_field(self, path: str) -> bool:
        """
        Validates if a required field in the dataset is present and not empty.

        Args:
            path (str): The path of the field to validate.

        Raises:
            ValueError: If the metadatablock specified in the path is not present in the dataset.

        Returns:
            List[bool]: True if the field is present and not empty, False otherwise.
        """

        metadatablock, *field = path.split("/")
        field_path = "/" + "/".join(field)

        if metadatablock not in self.metadatablocks:
            raise ValueError(
                f"Metadatablock '{metadatablock}' is not present in the dataset. Please use 'list_metadatablocks' to see which metadatablocks are registered."
            )

        metadatablock = nob.Nob(self.metadatablocks[metadatablock].dict())
        results = []
        field_exists = False

        for dspath in metadatablock.paths:
            meta_path = "/".join(
                [part for part in str(dspath).split("/") if not part.isdigit()]
            )

            if meta_path != field_path:
                continue
            else:
                field_exists = True

            if metadatablock[dspath].val is None:
                print(
                    f"⚠️ Field '{path}' is empty yet required. Please provide a value for this field."
                )

                results.append(False)

        if not field_exists:
            print(
                f"⚠️ Field '{path}' is not present in the dataset. Please provide a value for this field."
            )

            results.append(False)

        return len(results) == 0

    # ! Utilities
    def list_metadatablocks(self, detailed: bool = False):
        """Lists all metadatablocks present in this dataset instance"""

        for name, block in self.metadatablocks.items():
            if detailed:
                block.info()
            else:
                print(name)

    def list_files(self):
        """Lists all files present in the dataset for inspection"""
        for file in self.files:
            print(file.filepath)

    def replace_file(self, filename: str, local_path: str):
        """Replaces a given file which will be uploaded upon calling the 'update'-method

        Please note, this function is best used when replacing big files when the sole
        purpose is to update a file without downloading it. Hence, this method is best
        used in conjunction with the 'from_dataverse_doi' or 'from_url' method with
        'download_files' set to 'False'.
        """

        file = list(filter(lambda f: f.fileName == filename, self.files))

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

    def _keys_to_camel(self, dictionary: Dict):
        nu_dict = {}
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):
                nu_dict[self._snake_to_camel(key)] = self._keys_to_camel(
                    dictionary[key]
                )
            else:
                nu_dict[self._snake_to_camel(key)] = dictionary[key]
        return nu_dict

    # ! Overloads
    def __str__(self):
        return self.yaml()

    def __repr__(self):
        return self.yaml()
