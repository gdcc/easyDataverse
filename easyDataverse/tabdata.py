import os
from typing import Optional
import pandas as pd
import mimetypes
from pydantic import BaseModel, ConfigDict, Field, computed_field
from dvuploader import File

from rich.console import Console
from rich.table import Table


SEP_MAPPING = {
    "text/tab-separated-values": "\t",
    "text/csv": ",",
}


class Column(BaseModel):
    """
    Represents a column in a tabular data object.

    Attributes:
        name (str): The name of the column.
        dtype (str): The data type of the column.
    """

    name: str = Field(
        ...,
        description="The name of the column.",
    )

    dtype: str = Field(
        ...,
        description="The data type of the column.",
    )


class ColStats(BaseModel):
    """
    Represents the statistics of a column in a dataset.

    Attributes:
        count (int): The number of records in the column.
        mean (float, optional): The mean of the column.
        median (float, optional): The median of the column.
        std (float, optional): The standard deviation of the column.
        min (float, optional): The minimum value of the column.
        max (float, optional): The maximum value of the column.
        percentile_25 (float, optional): The 25th percentile of the column.
        percentile_75 (float, optional): The 75th percentile of the column.
    """

    count: int = Field(
        ...,
        description="The number of records in the column.",
    )

    mean: Optional[float] = Field(
        None,
        description="The mean of the column.",
    )

    median: Optional[float] = Field(
        None,
        description="The median of the column.",
    )

    std: Optional[float] = Field(
        None,
        description="The standard deviation of the column.",
    )

    min: Optional[float] = Field(
        None,
        description="The minimum value of the column.",
    )

    max: Optional[float] = Field(
        None,
        description="The maximum value of the column.",
    )

    percentile_25: Optional[float] = Field(
        None,
        description="The 25th percentile of the column.",
        alias="25%",
    )

    percentile_75: Optional[float] = Field(
        None,
        description="The 75th percentile of the column.",
        alias="75%",
    )


class TabData(BaseModel):
    """
    Represents a tabular data object.

    Attributes:
        model_config (ConfigDict): The model configuration dictionary.
        data (pd.DataFrame): The tabular data.
        name (str): The name of the tabular data.
        description (str): The description of the tabular data.
        directoryLabel (str): The directory label of the tabular data.
    """

    model_config: ConfigDict = {
        "arbitrary_types_allowed": True,
    }

    data: pd.DataFrame = Field(
        ...,
        description="The tabular data.",
    )

    name: str = Field(
        ...,
        description="The name of the tabular data.",
    )

    description: str = Field(
        ...,
        description="The description of the tabular data.",
    )

    directoryLabel: str = Field(
        ...,
        description="The directory label of the tabular data.",
    )

    @computed_field
    @property
    def stats(self) -> pd.DataFrame:
        """
        Returns the statistics of the tabular data.

        Returns:
            pd.DataFrame: The statistics of the tabular data.
        """

        stats = self.data.describe()
        col_stats = {}

        for col, stat in stats.to_dict().items():
            stat["median"] = stat.pop("50%")
            col_stats[col] = ColStats(**stat)

        return col_stats

    @computed_field
    @property
    def columns(self) -> pd.DataFrame:
        """
        Returns the columns of the tabular data.

        Returns:
            pd.DataFrame: The columns of the tabular data.
        """

        cols = {}

        for col, dtype in self.data.dtypes.to_dict().items():
            if dtype == "object":
                dtype = "string"
            else:
                dtype = dtype.name

            cols[col] = Column(name=col, dtype=dtype)

        return cols

    def prepare_upload(self, temp_dir: str) -> File:
        """
        Prepares the tabular data for upload to Dataverse.

        Args:
            temp_dir (str): The temporary directory to store the tabular data.

        Returns:
            str: The path to the tabular data file.
        """

        if "." not in self.name:
            filename = f"{self.name}.tab"
            mimetype = "text/tab-separated-values"
        elif self.name.endswith(".tab"):
            filename = self.name
            mimetype = "text/tab-separated-values"
        else:
            filename = self.name
            mimetype = mimetypes.guess_type(filename)[0]

            assert mimetype is not None, f"Could not determine mimetype for {filename}"

        if mimetype not in ["text/tab-separated-values", "text/csv"]:
            raise ValueError(f"Unsupported mimetype: {mimetype}")

        file_path = os.path.join(temp_dir, filename)
        self.data.to_csv(file_path, index=False, sep=SEP_MAPPING[mimetype])

        return File(
            filepath=file_path,
            description=self.description,
            directoryLabel=self.directoryLabel,
            mimeType=mimetype,  # type: ignore
        )

    def __str__(self) -> str:
        """
        Returns a string representation of the TabData object.

        The string representation includes a formatted table displaying the column names and data types.

        Returns:
            str: The string representation of the TabData object.
        """

        table = Table(
            title=f"[bold]{self.name}[/bold] - {self.data.shape[0]} rows x {self.data.shape[1]} columns",
            caption=self.description,
            caption_justify="left",
        )

        table.add_column("Column name", style="cyan", no_wrap=True)
        table.add_column("Data type", no_wrap=True)

        for col in self.columns.values():
            table.add_row(col.name, col.dtype)

        console = Console()
        console.print(table)

        return ""

    def to_json(self, **kwargs):
        """
        Convert the object to a JSON string.

        Args:
            **kwargs: Additional keyword arguments to be passed to the `model_dump` method.

        Returns:
            str: The JSON representation of the object.

        """
        return self.model_dump_json(exclude={"data"}, by_alias=True, **kwargs)

    def to_dict(self, **kwargs):
        """
        Convert the object to a dictionary.

        Args:
            **kwargs: Additional keyword arguments to be passed to the `model_dump` method.

        Returns:
            dict: The dictionary representation of the object.

        """
        return self.model_dump(exclude={"data"}, by_alias=True, **kwargs)
