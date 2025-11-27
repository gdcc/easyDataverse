from typing import List, Optional
from urllib import parse
from pydantic import BaseModel, ConfigDict, Field
import httpx


class License(BaseModel):
    """
    Represents a license for a Dataverse dataset.

    This class models the license information including name, URI, and other metadata
    that can be associated with a dataset in Dataverse.
    """

    name: str = Field(
        description="The name of the license",
    )

    uri: str = Field(
        description="The URI where the license text can be found",
    )

    id: int = Field(
        description="The internal ID of the license in Dataverse",
    )

    short_description: str = Field(
        alias="shortDescription",
        description="A brief description of the license",
    )

    active: bool = Field(
        description="Whether the license is active in the Dataverse instance",
    )

    is_default: bool = Field(
        alias="isDefault",
        description="Whether this is the default license in the Dataverse instance",
    )

    sort_order: int = Field(
        alias="sortOrder",
        description="The order in which the license appears in lists",
    )

    @classmethod
    def fetch_by_name(cls, name: str, server_url: str) -> "License":
        """
        Fetch a license by name from a Dataverse server.

        Args:
            name (str): The name of the license to fetch
            server_url (str): The base URL of the Dataverse server

        Returns:
            License: A License object with the requested license information

        Raises:
            Exception: If the license cannot be found or if there's an error communicating with the server
        """
        response = httpx.get(parse.urljoin(server_url, "/api/licenses"))

        if response.status_code != 200:
            raise Exception(f"Error getting licenses: {response.text}")

        licenses = response.json()["data"]

        try:
            return next(filter(lambda x: x["name"] == name, licenses))
        except StopIteration:
            raise Exception(f"License '{name}' not found at '{server_url}'")

    def to_json_ld(self):
        """
        Convert the license to JSON-LD format.

        Returns:
            dict: A dictionary containing the license information in JSON-LD format,
                  with the license URI mapped to the schema:license property.
        """
        return {
            "schema:license": self.uri,
        }

    @staticmethod
    def json_ld_field_names() -> List[str]:
        """
        Get the JSON-LD field names for the license.

        Returns:
            List[str]: A list of JSON-LD field names for the license.
        """
        return ["schema:license"]


class CustomLicense(BaseModel):
    """
    Represents a custom license for a Dataverse dataset.

    This class models the custom terms of use information including name, URI, and other metadata
    that can be associated with a dataset in Dataverse.
    """

    model_config = ConfigDict(
        populate_by_name=True,
    )

    terms_of_use: Optional[str] = Field(
        default=None,
        description="The terms of use of the dataset.",
        alias="termsOfUse",
    )

    confidentiality_declaration: Optional[str] = Field(
        default=None,
        description="The confidentiality declaration of the dataset.",
        alias="confidentialityDeclaration",
    )

    special_permissions: Optional[str] = Field(
        default=None,
        description="Special permissions for the dataset.",
        alias="specialPermissions",
    )

    restrictions: Optional[str] = Field(
        default=None,
        description="Restrictions applied to the dataset.",
        alias="restrictions",
    )

    citation_requirements: Optional[str] = Field(
        default=None,
        description="Requirements for citing the dataset.",
        alias="citationRequirements",
    )

    depositor_requirements: Optional[str] = Field(
        default=None,
        description="Requirements for depositors of the dataset.",
        alias="depositorRequirements",
    )

    conditions: Optional[str] = Field(
        default=None,
        description="Conditions for using the dataset.",
        alias="conditions",
    )

    disclaimer: Optional[str] = Field(
        default=None,
        description="Disclaimer for the dataset.",
        alias="disclaimer",
    )

    def to_json_ld(self):
        """Convert the custom license to JSON-LD format.

        Returns:
            dict: A dictionary with keys prefixed with 'dvcore:' containing
                  the license fields in JSON-LD format, excluding None values.
        """
        return {
            f"dvcore:{k}": v
            for k, v in self.model_dump(
                mode="json",
                exclude_none=True,
                by_alias=True,
            ).items()
        }

    @staticmethod
    def json_ld_field_names() -> List[str]:
        """
        Get the JSON-LD field names for the custom license.

        Returns:
            List[str]: A list of JSON-LD field names for the custom license.
        """
        return [
            f"dvcore:{field.alias}" for field in CustomLicense.model_fields.values()
        ]
