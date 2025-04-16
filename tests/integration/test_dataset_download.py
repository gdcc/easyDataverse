import json
import os
from typing import Dict

import pytest
import httpx

from easyDataverse import Dataverse


class TestDatasetDownload:
    @pytest.mark.integration
    def test_dataset_download_without_file(
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

        dataset = dataverse.load_dataset(pid)

        # Assert
        expected = self.sort_citation(minimal_upload)
        result = self.sort_citation(dataset.dataverse_dict())

        assert result == expected, (
            "The downloaded dataset does not match the expected dataset."
        )

    @pytest.mark.integration
    def test_dataset_download_with_file(
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

        # Add a file to the dataset
        url = f"{base_url}/api/datasets/:persistentId/add?persistentId={pid}"
        json_data = {"description": "Test"}
        with open("tests/fixtures/test_file.txt", "rb") as file:
            response = httpx.post(
                url=url,
                headers={
                    "X-Dataverse-key": api_token,
                },
                data={"jsonData": json.dumps(json_data)},
                files={"file": file},
            )

        response.raise_for_status()

        # Act
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        dataset = dataverse.load_dataset(pid)

        # Assert
        expected = self.sort_citation(minimal_upload)
        result = self.sort_citation(dataset.dataverse_dict())

        assert result == expected, (
            "The downloaded dataset does not match the expected dataset."
        )

        assert len(dataset.files) == 1, (
            "The dataset does not contain the expected number of files."
        )
        assert dataset.files[0].filepath == "./test_file.txt", (
            "The file path does not match the expected file path."
        )
        assert os.path.exists(dataset.files[0].filepath), "The file was not downloaded."
        assert (
            open("tests/fixtures/test_file.txt", "rb").read()
            == open(dataset.files[0].filepath, "rb").read()
        ), "The file content does not match the expected file content."

    @pytest.mark.integration
    def test_dataset_download_with_file_and_filter_pattern(
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

        # Add a file to the dataset
        url = f"{base_url}/api/datasets/:persistentId/add?persistentId={pid}"
        json_data = {"description": "Test"}
        with open("tests/fixtures/test_file.txt", "rb") as file:
            response = httpx.post(
                url=url,
                headers={
                    "X-Dataverse-key": api_token,
                },
                data={"jsonData": json.dumps(json_data)},
                files={"file": file},
            )

        response.raise_for_status()

        # Act
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        dataset = dataverse.load_dataset(
            pid=pid,
            filenames=[r"(\w+).txt", r"(\w+).py"],
        )

        # Assert
        expected = self.sort_citation(minimal_upload)
        result = self.sort_citation(dataset.dataverse_dict())

        assert result == expected, (
            "The downloaded dataset does not match the expected dataset."
        )

        assert len(dataset.files) == 1, (
            "The dataset does not contain the expected number of files."
        )
        assert dataset.files[0].filepath == "./test_file.txt", (
            "The file path does not match the expected file path."
        )
        assert os.path.exists(dataset.files[0].filepath), "The file was not downloaded."
        assert (
            open("tests/fixtures/test_file.txt", "rb").read()
            == open(dataset.files[0].filepath, "rb").read()
        ), "The file content does not match the expected file content."

    @staticmethod
    def sort_citation(dataset: Dict):
        citation = dataset["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fields = citation["fields"]
        dataset["datasetVersion"]["metadataBlocks"]["citation"]["fields"] = sorted(
            citation_fields,
            key=lambda x: x["typeName"],
        )

        return dataset
