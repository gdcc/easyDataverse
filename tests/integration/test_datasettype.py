import pytest
from easyDataverse.datasettype import DatasetType


class TestDatasetType:
    """Integration tests for DatasetType functionality."""

    @pytest.mark.integration
    def test_dataset_type_from_instance(self, credentials):
        """
        Test retrieving dataset types from a Dataverse instance.

        This test verifies that we can successfully fetch dataset types
        from a Dataverse installation and that the returned data matches
        the expected structure.

        Args:
            credentials: Fixture providing base_url and api_token for testing
        """
        base_url, _ = credentials
        dataset_types = DatasetType.from_instance(base_url)

        assert len(dataset_types) > 0
        expected_dataset_types = [
            DatasetType(id=1, name="dataset", linkedMetadataBlocks=[]),
        ]
        assert dataset_types == expected_dataset_types
