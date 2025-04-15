from pyDataverse.api import NativeApi
import pytest
from easyDataverse.dataverse import Dataverse


class TestConnection:
    @pytest.mark.integration
    def test_connection(self, credentials):
        # Arrange
        base_url, api_token = credentials

        # Act
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Assert
        assert str(dataverse.server_url).rstrip("/") == base_url
        assert str(dataverse.api_token) == api_token
        assert isinstance(dataverse.native_api, NativeApi)

    @pytest.mark.integration
    def test_dataset_creation(self, credentials):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        dataset = dataverse.create_dataset()

        # Assert
        assert str(dataset.API_TOKEN) == api_token
        assert str(dataset.DATAVERSE_URL).rstrip("/") == base_url
        assert len(dataset.metadatablocks) > 0
        assert hasattr(dataset, "citation")

        citation = dataset.citation
        assert citation is not None
        assert hasattr(citation, "title")
        assert hasattr(citation, "author")
        assert hasattr(citation, "dataset_contact")
        assert hasattr(citation, "ds_description")

    def test_numeric_namespace(self):
        # Harvard Dataverse hosts a metadata block with first letter numeric
        # attribute names. Hence, this tests checks if the numeric parts are
        # parsed correctly.

        try:
            Dataverse(server_url="https://dataverse.harvard.edu")
        except ValueError as e:
            AssertionError("Failed to parse numeric namespace: " + str(e))
