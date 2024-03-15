import pandas as pd
import pytest
from easyDataverse.tabdata import TabData


class TestTabData:

    @pytest.mark.unit
    def test_prepare_upload_no_extension(self):
        """
        Test case for the prepare_upload method of the TabData class.

        This test verifies that the prepare_upload method correctly prepares the tabular data for upload to Dataverse.

        Steps:
        1. Create a new instance of the TabData class.
        2. Create a sample DataFrame with two columns, 'A' and 'B'.
        3. Call the prepare_upload method of the tabular data instance, passing a temporary directory.
        4. Assert that the file path returned by the prepare_upload method exists.
        5. Assert that the file path returned by the prepare_upload method is equal to the expected file path.

        """
        # Arrange
        tab_data = TabData(
            data=pd.DataFrame(
                {
                    "A": [1, 2, 3],
                    "B": [4, 5, 6],
                }
            ),
            name="some_name",
            description="some_description",
            directoryLabel="some_dir",
        )
        temp_dir = "/tmp"

        # Act
        file = tab_data.prepare_upload(temp_dir)

        # Assert
        assert file.filepath == "/tmp/some_name.tab"
        assert file.description == "some_description"
        assert file.directoryLabel == "some_dir"
        assert file.mimeType == "text/tab-separated-values"

    @pytest.mark.unit
    def test_prepare_upload_tab_extension(self):
        """
        Test case for the prepare_upload method of TabData class when the file has a .tab extension.

        This test verifies that the prepare_upload method correctly prepares the TabData object for upload,
        including setting the file path, description, directory label, and MIME type.

        Steps:
        1. Create a TabData object with a DataFrame and other attributes.
        2. Call the prepare_upload method with a temporary directory.
        3. Assert that the file path is set correctly.
        4. Assert that the description is set correctly.
        5. Assert that the directory label is set correctly.
        6. Assert that the MIME type is set correctly.

        """
        # Arrange
        tab_data = TabData(
            data=pd.DataFrame(
                {
                    "A": [1, 2, 3],
                    "B": [4, 5, 6],
                }
            ),
            name="some_name.tab",
            description="some_description",
            directoryLabel="some_dir",
        )
        temp_dir = "/tmp"

        # Act
        file = tab_data.prepare_upload(temp_dir)

        # Assert
        assert file.filepath == "/tmp/some_name.tab"
        assert file.description == "some_description"
        assert file.directoryLabel == "some_dir"
        assert file.mimeType == "text/tab-separated-values"

    @pytest.mark.unit
    def test_prepare_upload_csv_extension(self):
        """
        Test case for the prepare_upload method of TabData class when the file has a .csv extension.

        This test verifies that the prepare_upload method correctly prepares the TabData object for upload,
        including setting the file path, description, directory label, and MIME type.

        Steps:
        1. Create a TabData object with a DataFrame and other attributes.
        2. Call the prepare_upload method with a temporary directory.
        3. Assert that the file path is set correctly.
        4. Assert that the description is set correctly.
        5. Assert that the directory label is set correctly.
        6. Assert that the MIME type is set correctly.

        """

        # Arrange
        tab_data = TabData(
            data=pd.DataFrame(
                {
                    "A": [1, 2, 3],
                    "B": [4, 5, 6],
                }
            ),
            name="some_name.csv",
            description="some_description",
            directoryLabel="some_dir",
        )
        temp_dir = "/tmp"

        # Act
        file = tab_data.prepare_upload(temp_dir)

        # Assert
        assert file.filepath == "/tmp/some_name.csv"
        assert file.description == "some_description"
        assert file.directoryLabel == "some_dir"
        assert file.mimeType == "text/csv"

    @pytest.mark.unit
    def test_prepare_upload_unknown_extension(self):
        """
        Test case for the prepare_upload method of TabData class when the file has an unknown extension.

        This test verifies that the prepare_upload method raises a ValueError when the file has an unknown extension.

        Steps:
        1. Create a TabData object with a DataFrame and other attributes.
        2. Call the prepare_upload method with a temporary directory.
        3. Assert that the prepare_upload method raises a ValueError.

        """
        # Arrange
        tab_data = TabData(
            data=pd.DataFrame(
                {
                    "A": [1, 2, 3],
                    "B": [4, 5, 6],
                }
            ),
            name="some_name.unknown",
            description="some_description",
            directoryLabel="some_dir",
        )
        temp_dir = "/tmp"

        # Act and Assert
        with pytest.raises(AssertionError):
            tab_data.prepare_upload(temp_dir)
