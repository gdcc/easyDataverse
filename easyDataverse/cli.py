import os
import typer

from easyDataverse import Dataset, ProgrammingLanguage
from easyDataverse.tools.codegen.generator import generate_python_api

app = typer.Typer()


@app.command()
def generate(
    path: str = typer.Option(..., help="Path to the metadatablock TSV files."),
    out: str = typer.Option(..., help="Path to which the API will be written."),
    name: str = typer.Option(..., help="Name of the resulting API."),
):
    """Generates Python API compliant to TSV metadatablocks.

    Args:
        path (str): Path to the metadatablock TSV files.
        out (str): Say hi formally.
        name (str): Name of the resulting API.
    """

    # Perform API generation
    generate_python_api(path, out, name)


@app.command()
def push(
    lang: ProgrammingLanguage = typer.Option(
        ..., help="Programming language to parse for metdata."
    ),
    dataverse: str = typer.Option(..., help="Target dataverse in your installation."),
    lib_name: str = typer.Option(
        ..., help="Library that is used to infer metadata schemes"
    ),
    token: str = typer.Option(
        "",
        help="API Token used to authenticate with the Dataverse. Can also be fetched from your env variables.",
    ),
    url: str = typer.Option(
        "",
        help="URL to the target Dataverse installation. Can also be fetched from your env variables.",
    ),
):
    """Pushes code and metadata to Dataverse.

    Args:
        lang (ProgrammingLanguage): Programming language to parse for metdata.
        dataverse (str): Target dataverse in your installation.
        lib_name (str): Library that is used to infer metadata schemes.
        token (str, optional): API Token used to authenticate with the Dataverse. Can also be fetched from your env variables.
        url (str, optional): URL to the target Dataverse installation. Can also be fetched from your env variables.
    """

    # Parse the repository
    dataset = Dataset.from_local_repository(
        programming_language=lang, lib_name=lib_name
    )

    # Upload to the target dataverse
    if not all([token, url]):
        # When no token and URL are specified, get from envs
        dataset.upload(dataverse)
    else:
        # If given, use those here
        dataset.upload(dataverse, API_TOKEN=token, DATAVERSE_URL=url)

    path = os.path.join(".", ".dataverse")
    with open(path, "w") as f:
        f.write(dataset.yaml())


@app.command()
def fetch(
    url: str = typer.Argument(..., help="URL to the dataset"),
    path: str = typer.Argument(".", help="Location where the data should be saved."),
):
    """Downloads files and metadata from a Dataverse installation.

    Args:
        url (str): URL to the dataset.
        path (str): Location where the data should be saved.
    """

    dataset = Dataset.from_url(url, path)

    with open(os.path.join(path, "metadata.yaml"), "w") as f:
        f.write(dataset.yaml())


def main():
    """Used to start the Typer app"""
    app()


if __name__ == "__main__":
    main()
