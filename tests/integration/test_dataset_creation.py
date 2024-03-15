import pandas as pd

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
            value="This is a description of the dataset"
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        assert self.sort_citation(dataset) == minimal_upload

    def test_creation_with_dataframe(
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
            value="This is a description of the dataset"
        )
        dataset.citation.add_dataset_contact(
            name="John Doe",
            email="john@doe.com",
        )

        data = pd.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            }
        )

        # Act
        dataset.add_dataframe(
            dataframe=data,
            name="some_name",
            dv_dir="some_dir",
            description="some_description",
        )

        # Assert
        assert "some_dir/some_name.tab" in dataset.tables
        assert dataset.tables["some_dir/some_name.tab"].data.equals(data)
        assert dataset.tables["some_dir/some_name.tab"].name == "some_name"
        assert (
            dataset.tables["some_dir/some_name.tab"].description == "some_description"
        )

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
