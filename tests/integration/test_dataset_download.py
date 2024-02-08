from typing import Dict

import pytest
import requests

from easyDataverse import Dataverse


class TestDatasetDownload:
    @pytest.mark.integration
    def test_dataset_download(
        self,
        credentials,
        minimal_upload,
    ):

        # Arrange
        base_url, api_token = credentials
        url = f"{base_url}api/dataverses/root/datasets"
        response = requests.post(
            url=url,
            json=minimal_upload,
            headers={
                "X-Dataverse-key": api_token,
                "Content-Type": "application/json",
            },
        )

        response.raise_for_status()
        pid = response.json()["data"]["persistentId"]

        # Act
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        dataset = dataverse.load_dataset(pid)

        # Assert
        expected = self.sort_citation(minimal_upload)
        result = self.sort_citation(dataset.dataverse_dict())

        assert (
            result == expected
        ), "The downloaded dataset does not match the expected dataset."

    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset
