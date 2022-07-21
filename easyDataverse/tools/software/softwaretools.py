import importlib
import os
from typing import Optional

from easyDataverse.tools.software.pythonparser import python_parser
from easyDataverse.tools.software.softwareinfo import SoftwareInfo, ProgrammingLanguage

# ! Globals
REQUIRED_META = ["Citation", "CodeMeta"]

# ! Mappings

parser_mapping = {ProgrammingLanguage.PYTHON: python_parser}

# ! Functions


def dataset_from_repository(
    lang: ProgrammingLanguage,
    lib_name: Optional[str] = None,
):
    """Used to parse a software repository."""

    # import metadata configuration
    metadatablocks = _fetch_meta_config(lib_name)

    # Fetch all the information if given
    repo_meta = parser_mapping[lang]()

    # Build a dataset now and push it to the specified dataverse
    citation = getattr(metadatablocks.citation, "Citation")()
    subject_enum = getattr(metadatablocks.citation, "SubjectEnum")
    codemeta = getattr(metadatablocks.codeMeta, "CodeMeta")()

    citation.title = f"{repo_meta.name}"
    citation.subject = [subject_enum.computer_and__information__science]
    citation.add_author(repo_meta.author)
    citation.add_contact(name=citation.author[0].name, email=repo_meta.author_email)
    citation.add_description(text=repo_meta.description)

    codemeta.software_version = repo_meta.version
    codemeta.programming_language = [lang]

    for package in repo_meta.packages:
        codemeta.add_software_requirements(name=package.name, url=package.url)

    return citation, codemeta


def _fetch_meta_config(lib_name: Optional[str] = None):
    """Fetches metadata configurations from the current API"""

    if not lib_name:
        lib_name = os.environ["EASYDATAVERSE_LIB_NAME"]

    metadatablocks = importlib.import_module(f".metadatablocks", lib_name)

    for block in REQUIRED_META:
        if not hasattr(metadatablocks, block):
            # Check minimum requirements
            raise ModuleNotFoundError(
                f"Metadata block configuration {block} not supported by {lib_name}, but are required."
            )

    return metadatablocks
