from typing import Dict

import pytest
import httpx

from easyDataverse import Dataverse
from easyDataverse.license import CustomLicense, License


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
    def test_custom_license_update(
        self,
        credentials,
        minimal_upload_custom_license,
    ):
        # Arrange
        base_url, api_token = credentials
        url = f"{base_url}/api/dataverses/root/datasets"
        response = httpx.post(
            url=url,
            json=minimal_upload_custom_license,
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

        # Fetch the dataset and update the license
        dataset = dataverse.load_dataset(pid)
        dataset.license = CustomLicense(
            termsOfUse="CHANGED",
            confidentialityDeclaration="CHANGED",
            specialPermissions="CHANGED",
            restrictions="CHANGED",
            citationRequirements="CHANGED",
            conditions="CHANGED",
            depositorRequirements="CHANGED",
            disclaimer="CHANGED",
        )

        dataset.update()

        # Re-fetch the dataset
        refetched_dataset = dataverse.load_dataset(pid)

        # Assert
        assert isinstance(refetched_dataset.license, CustomLicense)
        assert refetched_dataset.license.terms_of_use == "CHANGED"
        assert refetched_dataset.license.confidentiality_declaration == "CHANGED"
        assert refetched_dataset.license.special_permissions == "CHANGED"
        assert refetched_dataset.license.restrictions == "CHANGED"
        assert refetched_dataset.license.citation_requirements == "CHANGED"
        assert refetched_dataset.license.conditions == "CHANGED"
        assert refetched_dataset.license.depositor_requirements == "CHANGED"
        assert refetched_dataset.license.disclaimer == "CHANGED"

        assert dataset.dataverse_dict() == refetched_dataset.dataverse_dict(), (
            "Dataset contents are not the same"
        )

    @pytest.mark.integration
    def test_custom_license_update_with_predefined_license(
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

        # Fetch the dataset and update the license
        dataset = dataverse.load_dataset(pid)
        assert isinstance(dataset.license, License), (
            "Dataset license is not a predefined license"
        )

        # Update the license to a different predefined license
        expected_license = next(
            license
            for license in dataverse.licenses.values()
            if license.name != dataset.license.name
        )
        dataset.license = expected_license

        dataset.update()

        # Re-fetch the dataset
        refetched_dataset = dataverse.load_dataset(pid)

        # Assert
        assert refetched_dataset.license == expected_license, (
            "Dataset license is not the expected license"
        )

        assert dataset.dataverse_dict() == refetched_dataset.dataverse_dict(), (
            "Dataset contents are not the same"
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
