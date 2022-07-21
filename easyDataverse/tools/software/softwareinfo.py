from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class ProgrammingLanguage(Enum):

    PYTHON = "Python"
    # CPP = "C++"


@dataclass
class Package:
    """Structure to report on a software package"""

    name: str
    url: Optional[str]


@dataclass
class SoftwareInfo:
    """Structure to store metadata of a software. Results from parsing a repository."""

    name: str
    version: str
    packages: List[Package]
    author: str
    license: str
    author_email: str = "nomail@provided.com"
    description: str = (
        "No description provided. Please add manually via the Dataverse GUI!"
    )
    programming_language: Optional[str] = None
