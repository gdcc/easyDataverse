<h1 align="center">
  <img src="https://raw.githubusercontent.com/gdcc/easyDataverse/main/static/logo.png" width=300 alt="EasyDataverse"></br>
  <img src="https://img.shields.io/badge/EasyDataverse-0.4.0-blue" alt="v0.4.0">
  <img src="https://img.shields.io/badge/python-3.8 | 3.9 | 3.10 | 3.11 -blue.svg" alt="Build Badge">
  <img src="https://github.com/gdcc/easyDataverse/actions/workflows/unit-tests.yaml/badge.svg" alt="Build Badge">
  <img src="https://github.com/gdcc/easyDataverse/actions/workflows/integration-tests.yaml/badge.svg" alt="Build Badge">
</h1>

<p align="center">
EasyDataverse is a Python library used to interface Dataverse installations and dynamically generate Python objects compatible to a metadatablock configuration given at a Dataverse installation. In addition, EasyDataverse allows you to export and import datasets to and from various data formats.</p>

### Features

- **Metadataconfig compliant** classes for flexible Dataset creation.
- **Upload and download** of files and directories to and from Dataverse installations.
- **Export and import** of datasets to various formats (JSON, YAML and XML).
- **Fetch datasets** from any Dataverse installation into an object oriented structure ready to be integrated.

## ⚡️ Quick start

Get started with EasyDataverse by running the following command

```bash
# Using PyPI
pip install easyDataverse
```

Or build by source

```bash
pip install git+https://github.com/gdcc/easyDataverse.git
```

## ⚙️ Quickstart

### Dataset creation

EasyDataverse is capable of connecting to a given Dataverse installation and fetch all metadata fields and their properties. This allows you to create a dataset object with all the metadata fields and their properties given at the Dataverse installation.

```python
from easyDataverse import Dataverse

# Connect to a Dataverse installation
dataverse = Dataverse(
  server_url="https://demo.dataverse.org",
  api_token="MY_API_TOKEN",
)

# Initialize a dataset
dataset = dataverse.create_dataset()

# Fill metadata blocks
dataset.citation.title = "My dataset"
dataset.citation.subject = ["Other"]
dataset.citation.add_author(name="John Doe")
dataset.citation.add_dataset_contact(name="John Doe", email="john@doe.com")
dataset.citation.add_ds_description(value="This is a description of the dataset")

# Upload files or directories
dataset.add_file(local_path="./my.file", dv_dir="some/dir")
dataset.add_directory(dirpath="./my_directory", dv_dir="some/dir")

# Upload to the dataverse instance
dataset.upload("my_dataverse_id")
```

### Dataset download and update

EasyDataset allows you to download datasets from any Dataverse installation. The downloaded dataset is represented as an object oriented structure and can be used to update metadata/files, export a dataset to various formats or use it in subsequent applications.

```python
# Method 1: Download a dataset by its DOI
dataverse = Dataverse("https://demo.dataverse.org")
dataset = dataverse.load_dataset(
    pid="doi:10.70122/FK2/W5AGKD",
    version="1",
    filedir="place/for/data",
)

# Method 2: Download via URL
dataset, dataverse = Dataverse.from_ds_url(
    url="https://demo.dataverse.org/dataset.xhtml?persistentId=doi:10.70122/XX/XXXXX&version=DRAFT",
    api_token="MY_API_TOKEN"
)

# Display the content of the dataset
print(dataset)

# Update metadata
dataset.citation.title = "My even nicer dataset"

# Synchronize with the dataverse instance
dataset.update()
```

## 📖 Documentation and more examples

You can find a thorough [example notebook](examples/EasyDataverseBasics.ipynb) in the [examples](examples) directory. This notebook demonstrate basic concepts of EasyDataverse and how to use it in practice.

## ✍️ Authors

- Jan Range (EXC2075 SimTech, University of Stuttgart)

## ⚠️ License

`EasyDataverse` is free and open-source software licensed under the [MIT License](LICENSE).
