import os
import typer

from easyDataverse import Dataverse

app = typer.Typer()


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

    dataset, _ = Dataverse.load_from_url(url=url, filedir=path)

    with open(os.path.join(path, "metadata.yaml"), "w") as f:
        f.write(dataset.yaml())


def main():
    """Used to start the Typer app"""
    app()


if __name__ == "__main__":
    main()
