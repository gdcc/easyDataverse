from typing import List
from urllib.parse import urljoin
from pydantic import BaseModel, Field
import httpx
from pyDataverse.api import NativeApi


class DatasetType(BaseModel):
    """
    Represents a dataset type in Dataverse.

    A dataset type defines the structure and metadata requirements for datasets
    in a Dataverse instance, including which metadata blocks are linked to it.
    """

    id: int = Field(..., description="The ID of the dataset type")
    name: str = Field(..., description="The name of the dataset type")
    linkedMetadataBlocks: list[str] = Field(
        default_factory=list,
        description="The metadata blocks linked to the dataset type",
    )

    @classmethod
    def from_instance(cls, base_url: str) -> List["DatasetType"]:
        """
        Retrieve all dataset types from a Dataverse instance.

        Args:
            base_url: The base URL of the Dataverse instance

        Returns:
            A list of DatasetType objects representing all dataset types
            available in the Dataverse instance

        Raises:
            httpx.HTTPStatusError: If the API request fails
            ValueError: If the Dataverse instance is not at least version 6.4
        """
        native_api = NativeApi(base_url=base_url)

        if cls._get_version(native_api) < (6, 4):
            raise ValueError(
                "Dataset types are only supported in Dataverse 6.4 and above"
            )

        url = urljoin(native_api.base_url, "api/datasets/datasetTypes")
        response = httpx.get(url)

        if not response.is_success:
            # If there are no dataset types, the response is a 200 with an empty list
            return []

        return [cls.model_validate(item) for item in response.json()["data"]]

    @staticmethod
    def _get_version(native_api: NativeApi) -> tuple[int, int]:
        """
        Get the version of the Dataverse instance.
        """
        response = native_api.get_info_version()
        response.raise_for_status()
        version = response.json()["data"]["version"]
        major, minor = version.split(".", 1)
        return int(major), int(minor)
