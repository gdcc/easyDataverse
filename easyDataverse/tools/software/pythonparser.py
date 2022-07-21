import glob
import re
import requests

from typing import Optional, Dict, List

from easyDataverse.tools.software.softwareinfo import (
    SoftwareInfo,
    Package,
    ProgrammingLanguage,
)

# * Constants

PYTHON_SETUP_FIELDS = ["name", "version", "author", "license", "author_email"]


def python_parser():
    """Parses a Python software repository and extracts metadata necessary for a Dataverse dataset.

    This parser is specifically set up to localize either 'setup.py' or 'pyproject.toml' files
    and gets all the information from them. The returned object is a SoftwareInfo object which
    contains all necessary information about the repository and will further passed to the
    'from_software' classmethod of a Dataset object to gather information automatically.
    """

    if _has_setup_file():
        parse_fun = _parse_setup_file
    elif _has_pyproject_file():
        raise NotImplementedError("Not yet there, but will come!")
    else:
        return None

    # Parse the corresponding file
    software_info = parse_fun()
    software_info.programming_language = ProgrammingLanguage.PYTHON.value

    return software_info


# ! Checkers


def _has_setup_file() -> bool:
    """Checks whether a 'setup.py' file exists."""
    return any("setup.py" in path for path in glob.glob("*"))


def _has_pyproject_file() -> bool:
    """Checks whether a 'pyproject.toml' file exists."""
    return any("pyproject.toml" in path for path in glob.glob("*"))


# ! Helpers


def _parse_setup_file() -> SoftwareInfo:
    """Parses a setup.py file and extracts metadata necessary for a Dataverse dataset."""

    # Set up pattern matching for the setup file
    setup_file = open("setup.py", "r").read()

    # Retrieve metadata from the setup file
    metadata = _get_setup_metadata(setup_file)

    # Retrieve all packages from the setup file
    packages = _get_required_packages(setup_file)

    return SoftwareInfo(**metadata, packages=packages)


def _get_setup_metadata(setup_file: str) -> Dict:
    """Retrieves metadata defined in PYTHON_SETUP_FIELDS from setup.py."""

    # Set up regular expressions
    pattern_setup = r"([A-Za-z\_]*)\s?\=\s?\"?([A-Za-z\d\.\s\_]*)\"?"
    regex_setup = re.compile(pattern_setup)

    pattern_dict = r"\"([A-Za-z\_]*)\"\s?\:\s?\"?([A-Za-z\d\.\s\_]*)\"?"
    regex_dict = re.compile(pattern_dict)

    # Parse setup file and retrieve metadata
    results = regex_dict.findall(setup_file) + regex_setup.findall(setup_file)
    metadata = set(filter(lambda tup: tup[0] in PYTHON_SETUP_FIELDS, results))

    # Turn set into a dictionary to set up the SoftwareInfo class
    return {key: value for key, value in metadata}


def _get_required_packages(setup_file: str) -> List:
    """Retrieve required packages from setup.py."""

    # Extract packages present in setup.py
    packages_pattern = r"\"?install_requires\"?\s?[\:\=]\s?\[([A-Za-z0-9\"\,\s]*)\]"
    regex = re.compile(packages_pattern)
    results = regex.findall(setup_file.replace("\n", ""))[0]
    pkg_names = list(
        map(lambda package: package.strip().replace('"', ""), results.split(","))
    )

    # Fetch URL to packages
    packages = [
        Package(name=pkg, url=_fetch_url_from_pypi(pkg)) for pkg in pkg_names if pkg
    ]

    return packages


def _fetch_url_from_pypi(package: str) -> Optional[str]:
    """Searches PyPI for a package and return the repository/pypi URL"""

    # Fetch from PyPI REST API
    header = {"content-type": "application/json"}
    url = f"https://pypi.org/pypi/{package}/json"
    response = requests.get(url, headers=header)
    metadata = response.json()["info"]

    if response.status_code != 200:
        # May not available at PyPi
        return None

    if metadata.get("project_url"):
        # If there is a specific repo URL
        return metadata["project_url"]
    else:
        # If not, send the PyPI link
        return metadata["package_url"]
