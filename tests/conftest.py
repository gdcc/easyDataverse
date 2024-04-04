import pytest
import os
import json


@pytest.fixture()
def credentials():
    """
    Retrieves the base URL and API token from the environment variables.

    Returns:
        tuple: A tuple containing the base URL and API token.
    """
    return (
        os.environ.get("BASE_URL").rstrip("/"),
        os.environ.get("API_TOKEN"),
    )


@pytest.fixture()
def minimal_upload():
    """
    Returns the contents of the 'minimal_upload.json' file as a dictionary.

    Returns:
        dict: The contents of the 'minimal_upload.json' file.
    """
    return json.load(open("tests/fixtures/minimal_upload.json"))
