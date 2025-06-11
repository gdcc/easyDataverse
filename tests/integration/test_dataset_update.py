from typing import Dict

import pytest
import httpx

from easyDataverse import Dataverse


class TestDatasetUpdate:
    @pytest.mark.integration
    def test_dataset_update(
        self,
        credentials,
        minimal_upload,
    ):
        # Arrange
        base_url, api_token = credentials
        url = f"{base_url}/api/dataverses/root/datasets"
        response = httpx.post(
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

        # Fetch the dataset and update the title
        dataset = dataverse.load_dataset(pid)
        dataset.citation.title = "Title has changed"  # type: ignore
        dataset.update()

        # Re-fetch the dataset
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = httpx.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_dataset = response.json()
        title_field = next(
            filter(
                lambda x: x["typeName"] == "title",
                updated_dataset["data"]["metadataBlocks"]["citation"]["fields"],
            )
        )

        # Assert
        assert title_field["value"] == "Title has changed", (
            "The updated dataset title does not match the expected title."
        )

    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset
