from typing import Dict

import pytest
import requests

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

        # Fetch the dataset and update the title
        dataset = dataverse.load_dataset(pid)
        dataset.citation.title = "Title has changed"

        # Check if multiple compound changes are tracked too
        dataset.citation.add_other_id(agency="Software Heritage1", value="softwareid1")
        dataset.citation.add_other_id(agency="Software Heritage2", value="softwareid2")

        dataset.update()

        # Re-fetch the dataset
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = requests.get(
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

        other_id_fields = next(
            filter(
                lambda x: x["typeName"] == "otherId",
                updated_dataset["data"]["metadataBlocks"]["citation"]["fields"],
            )
        )["value"]

        # Assert
        assert (
            title_field["value"] == "Title has changed"
        ), "The updated dataset title does not match the expected title."
        assert (
            len(other_id_fields) == 2
        ), "The updated dataset does not have the expected number of other ids."
        assert (
            other_id_fields[0]["otherIdValue"]["value"] == "softwareid1"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[1]["otherIdValue"]["value"] == "softwareid2"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[0]["otherIdAgency"]["value"] == "Software Heritage1"
        ), "The updated dataset does not have the expected other id agency."
        assert (
            other_id_fields[1]["otherIdAgency"]["value"] == "Software Heritage2"
        ), "The updated dataset does not have the expected other id agency."

    @pytest.mark.integration
    def test_dataset_update_wo_replace(
        self,
        credentials,
        minimal_upload,
    ):
        # Arrange
        base_url, api_token = credentials
        url = f"{base_url}/api/dataverses/root/datasets"
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

        # Fetch the dataset and update the title
        dataset = dataverse.load_dataset(pid)

        # Check if multiple compound changes are tracked too
        dataset.citation.add_other_id(agency="Software Heritage1", value="softwareid1")
        dataset.citation.add_other_id(agency="Software Heritage2", value="softwareid2")

        dataset.update(replace=False)

        # Re-fetch the dataset
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = requests.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_dataset = response.json()
        other_id_fields = next(
            filter(
                lambda x: x["typeName"] == "otherId",
                updated_dataset["data"]["metadataBlocks"]["citation"]["fields"],
            )
        )["value"]

        # Assert
        assert (
            len(other_id_fields) == 2
        ), "The updated dataset does not have the expected number of other ids."
        assert (
            other_id_fields[0]["otherIdValue"]["value"] == "softwareid1"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[1]["otherIdValue"]["value"] == "softwareid2"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[0]["otherIdAgency"]["value"] == "Software Heritage1"
        ), "The updated dataset does not have the expected other id agency."
        assert (
            other_id_fields[1]["otherIdAgency"]["value"] == "Software Heritage2"
        ), "The updated dataset does not have the expected other id agency."


    @pytest.mark.integration
    def test_update_edit(
        self,
        credentials,
        minimal_upload,
    ):
        # Arrange
        base_url, api_token = credentials
        url = f"{base_url}/api/dataverses/root/datasets"
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

        # Fetch the dataset and update the title
        dataset = dataverse.load_dataset(pid)

        # Check if multiple compound changes are tracked too
        dataset.citation.add_other_id(agency="Software Heritage1", value="softwareid1")
        dataset.citation.add_other_id(agency="Software Heritage2", value="softwareid2")

        dataset.update(replace=False)

        # Fetch another time and edit the first entry
        dataset = dataverse.load_dataset(pid)
        dataset.citation.other_id[0].agency = "Software Heritage1 updated"

        dataset.update(replace=False)

        # Re-fetch the dataset
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = requests.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_dataset = response.json()
        other_id_fields = next(
            filter(
                lambda x: x["typeName"] == "otherId",
                updated_dataset["data"]["metadataBlocks"]["citation"]["fields"],
            )
        )["value"]

        # Assert
        assert (
            len(other_id_fields) == 2
        ), "The updated dataset does not have the expected number of other ids."
        assert (
            other_id_fields[0]["otherIdValue"]["value"] == "softwareid1"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[1]["otherIdValue"]["value"] == "softwareid2"
        ), "The updated dataset does not have the expected other id."
        assert (
            other_id_fields[0]["otherIdAgency"]["value"] == "Software Heritage1 updated"
        ), "The updated dataset does not have the expected other id agency."
        assert (
            other_id_fields[1]["otherIdAgency"]["value"] == "Software Heritage2"
        ), "The updated dataset does not have the expected other id agency."


    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset
