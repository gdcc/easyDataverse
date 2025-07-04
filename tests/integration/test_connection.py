import pytest

from pyDataverse.api import NativeApi
from easyDataverse.license import License
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

    def test_license_list(self, credentials):
        # Arrange
        base_url, api_token = credentials
        dataverse = Dataverse(
            server_url=base_url,
            api_token=api_token,
        )

        # Act
        licenses = dataverse.licenses
        default_license = dataverse.default_license

        # Assert
        assert len(licenses) > 0
        assert isinstance(licenses, dict)
        assert isinstance(list(licenses.values())[0], License)

        assert isinstance(default_license, License)
        assert default_license.is_default
        assert default_license.name == "CC0 1.0"

    def test_numeric_namespace(self):
        # Harvard Dataverse hosts a metadata block with first letter numeric
        # attribute names. Hence, this tests checks if the numeric parts are
        # parsed correctly.

        try:
            Dataverse(server_url="https://dataverse.harvard.edu")
        except ValueError as e:
            AssertionError("Failed to parse numeric namespace: " + str(e))

    @pytest.mark.integration
    def test_version_borealis(self):
        """Tests compatibility with BorealisData, which uses a different versioning scheme."""
        Dataverse("https://borealisdata.ca/")
