import pytest
from easyDataverse.dataset import Dataset
import pandas as pd


class TestDataset:
    def test_add_dataframe(self):
        """
        Test case for the add_dataframe method of the Dataset class.

        This test verifies that the add_dataframe method correctly adds a DataFrame to the dataset.

        Steps:
        1. Create a new instance of the Dataset class.
        2. Create a sample DataFrame with two columns, 'A' and 'B'.
        3. Call the add_dataframe method of the dataset instance, passing the sample DataFrame and a name for the table.
        4. Assert that the table with the specified name exists in the dataset's tables dictionary.
        5. Assert that the table with the specified name is equal to the original DataFrame.

        """
        # Arrange
        dataset = Dataset()
        data = pd.DataFrame(
            {
                "A": [1, 2, 3],
                "B": [4, 5, 6],
            }
        )

        # Act
        dataset.add_dataframe(
            dataframe=data,
            name="some_name",
            dv_dir="some_dir",
            description="some_description",
        )

        # Assert
        assert "some_dir/some_name.tab" in dataset.tables
        assert dataset.tables["some_dir/some_name.tab"].data.equals(data)
        assert dataset.tables["some_dir/some_name.tab"].name == "some_name"
        assert (
            dataset.tables["some_dir/some_name.tab"].description == "some_description"
        )

    def test_add_dataframe_wrong_type(self):
        """
        Test case for the add_dataframe method of the Dataset class.

        This test verifies that the add_dataframe method raises a TypeError when the wrong type is passed.

        Steps:
        1. Create a new instance of the Dataset class.
        2. Create a sample string.
        3. Call the add_dataframe method of the dataset instance, passing the sample string and a name for the table.
        4. Assert that the add_dataframe method raises a TypeError.

        """
        # Arrange
        dataset = Dataset()
        data = "some string"

        # Act and Assert
        with pytest.raises(TypeError):
            dataset.add_dataframe(
                dataframe=data,
                name="some_name",
                dv_dir="some_dir",
                description="some_description",
            )
