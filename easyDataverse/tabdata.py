import os
import pandas as pd
import mimetypes
from pydantic import BaseModel, ConfigDict
from dvuploader import File


SEP_MAPPING = {
    "text/tab-separated-values": "\t",
    "text/csv": ",",
}


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

    data: pd.DataFrame
    name: str
    description: str
    directoryLabel: str

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

    def __repr__(self) -> str:
        return f"TabData(name={self.name}, description={self.description})"
