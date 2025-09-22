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

    @pytest.mark.integration
    def test_dataset_update_with_multiple_fields(
        self,
        credentials,
    ):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Create a dataset
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

        pid = dataset.upload("Root")

        # Act
        # Re-fetch the dataset and add other ID
        dataset = dataverse.load_dataset(pid)
        dataset.citation.add_other_id(agency="DOI", value="10.5072/easy-dataverse")
        dataset.update()

        # Re-fetch the dataset to verify the update
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = httpx.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_dataset = response.json()
        other_id_field = next(
            filter(
                lambda x: x["typeName"] == "otherId",
                updated_dataset["data"]["metadataBlocks"]["citation"]["fields"],
            ),
            None,
        )

        # Assert
        assert other_id_field is not None, "Other ID field should be present"
        assert len(other_id_field["value"]) > 0, "Other ID field should have values"
        assert any(
            item["otherIdAgency"]["value"] == "DOI"
            and item["otherIdValue"]["value"] == "10.5072/easy-dataverse"
            for item in other_id_field["value"]
        ), "The DOI other ID should be present in the updated dataset"

    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset
