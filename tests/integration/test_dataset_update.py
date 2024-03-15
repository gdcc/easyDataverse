from io import StringIO
import json
import pandas as pd
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

        # Assert
        assert (
            title_field["value"] == "Title has changed"
        ), "The updated dataset title does not match the expected title."

    @pytest.mark.integration
    def test_dataset_update_with_tabular_data(
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

        # Add a file to the dataset
        url = f"{base_url}/api/datasets/:persistentId/add?persistentId={pid}"
        json_data = {"description": "Test"}
        response = requests.post(
            url=url,
            headers={
                "X-Dataverse-key": api_token,
            },
            data={"jsonData": json.dumps(json_data)},
            files={"file": open("tests/fixtures/data.tab", "rb")},
        )

        # Act
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Fetch the dataset and update the title
        dataset = dataverse.load_dataset(pid)
        df = dataset.tables["data.tab"].data
        dataset.tables["data.tab"].data = df * 10
        dataset.update()

        self.wait_for_lock_removal(base_url, api_token, pid)

        # Re-fetch the dataset and grab the updated tabular data
        url = (
            f"{base_url}/api/datasets/:persistentId/versions/:draft?persistentId={pid}"
        )

        response = requests.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_dataset = response.json()
        updated_tabular_data = updated_dataset["data"]["files"][0]

        # Fetch dataset file
        url = f"{base_url}/api/access/datafile/{updated_tabular_data['dataFile']['id']}"
        response = requests.get(
            url,
            headers={"X-Dataverse-key": api_token},
        )

        response.raise_for_status()
        updated_data = pd.read_csv(
            StringIO(response.content.decode("utf-8")),
            sep="\t",
        )

        # Assert
        assert updated_data.equals(
            df * 10
        ), "The updated dataset does not match the expected dataset."

    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset

    @staticmethod
    def wait_for_lock_removal(base_url, api_token, pid):
        url = f"{base_url}/api/datasets/:persistentId/locks?persistentId={pid}"
        response = requests.get(
            url=url,
            headers={
                "X-Dataverse-key": api_token,
            },
        )

        response.raise_for_status()
        locks = response.json()["data"]
        while locks:
            response = requests.get(
                url=url,
                headers={
                    "X-Dataverse-key": api_token,
                },
            )

            response.raise_for_status()
            locks = response.json()["data"]
