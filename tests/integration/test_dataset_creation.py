import os
from pydantic import ValidationError
import pytest
from easyDataverse.dataset import Dataset

from easyDataverse.dataverse import Dataverse
from easyDataverse.license import CustomLicense


class TestDatasetCreation:
    @pytest.mark.integration
    def test_creation(
        self,
        credentials,
        minimal_upload,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        dataset.add_directory(
            dirpath="./tests/fixtures",
            dv_dir="some/sub/dir",
        )

        assert self.sort_citation(dataset) == minimal_upload

    @pytest.mark.integration
    def test_creation_and_upload(
        self,
        credentials,
        minimal_upload,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        dataset.add_directory(
            dirpath="./tests/fixtures",
            dv_dir="some/sub/dir",
        )

        pid = dataset.upload(dataverse_name="root")

        # Re-fetch the dataset
        dataset = dataverse.load_dataset(pid)

        # Check the metadata
        assert self.sort_citation(dataset) == minimal_upload

        # Check the files
        expected_file_count = self.count_files_recursively("./tests/fixtures")
        assert len(dataset.files) == expected_file_count, (
            f"The number of files should be correct: Got {len(dataset.files)}, expected {expected_file_count}"
        )

        # Check if files have uploaded in the correct directory
        for file in dataset.files:
            assert "some/sub/dir" in file.directory_label, (
                "File should be in the sub-directory"
            )

    @pytest.mark.integration
    def test_double_upload_raises_error(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        dataset.add_directory(
            dirpath="./tests/fixtures",
            dv_dir="some/sub/dir",
        )

        dataset.upload(dataverse_name="root")

        with pytest.raises(ValueError):
            dataset.upload(dataverse_name="root")

    @pytest.mark.integration
    def test_creation_and_upload_with_dataset_type(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        dataset.dataset_type = "dataset"
        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        pid = dataset.upload(dataverse_name="root")

        # Re-fetch the dataset
        dataset = dataverse.load_dataset(pid)

        assert dataset.dataset_type == "dataset"

    @pytest.mark.integration
    def test_creation_invalid_dataset_type(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        with pytest.raises(ValidationError):
            dataset.dataset_type = "invalid"

    @pytest.mark.integration
    def test_creation_other_license(
        self,
        credentials,
        minimal_upload_other_license,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()
        dataset.license = dataverse.licenses["CC BY 4.0"]

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        dataset.add_directory(
            dirpath="./tests/fixtures",
            dv_dir="some/sub/dir",
        )

        assert self.sort_citation(dataset) == minimal_upload_other_license

    @pytest.mark.integration
    def test_creation_custom_terms_of_use(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()
        dataset.license = CustomLicense(
            termsOfUse="This is a custom terms of use",
            confidentialityDeclaration="This is a custom confidentiality declaration",
            specialPermissions="This is a custom special permissions",
            restrictions="This is a custom restrictions",
            citationRequirements="This is a custom citation requirements",
            depositorRequirements="This is a custom depositor requirements",
            conditions="This is a custom conditions",
            disclaimer="This is a custom disclaimer",
        )

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        pid = dataset.upload(dataverse_name="root")

        # Re-fetch the dataset
        dataset = dataverse.load_dataset(pid)

        # Check the terms of use
        assert isinstance(dataset.license, CustomLicense)
        license = dataset.license
        assert license.terms_of_use == "This is a custom terms of use"
        assert license.special_permissions == "This is a custom special permissions"
        assert license.restrictions == "This is a custom restrictions"
        assert license.citation_requirements == "This is a custom citation requirements"
        assert license.conditions == "This is a custom conditions"
        assert license.disclaimer == "This is a custom disclaimer"
        assert (
            license.confidentiality_declaration
            == "This is a custom confidentiality declaration"
        )
        assert (
            license.depositor_requirements == "This is a custom depositor requirements"
        )

    @pytest.mark.integration
    def test_tab_ingest_disabled(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        dataset.citation.title = "My dataset"
        dataset.citation.subject = ["Other"]
        dataset.citation.add_author(name="John Doe")
        dataset.citation.add_ds_description(
            value="This is a description of the dataset",
            date="2024",
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        dataset.add_file(
            local_path="./tests/fixtures/tabular_file.csv",
            tab_ingest=False,
        )

        assert dataset.files[0].tab_ingest is False, "Tab-ingest should be disabled"

    @staticmethod
    def sort_citation(dataset: Dataset):
        dv_dict = dataset.dataverse_dict()
        del dv_dict["datasetType"]
        citation = dv_dict["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dv_dict["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dv_dict

    @staticmethod
    def count_files_recursively(dirpath: str):
        count = 0
        for root, dirs, files in os.walk(dirpath):
            count += len(files)
        return count
