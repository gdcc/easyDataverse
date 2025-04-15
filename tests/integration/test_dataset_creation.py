import pytest
from easyDataverse.dataset import Dataset

from easyDataverse.dataverse import Dataverse


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

    @staticmethod
    def sort_citation(dataset: Dataset):
        dv_dict = dataset.dataverse_dict()
        citation = dv_dict["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dv_dict["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dv_dict
