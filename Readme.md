<h1 align="center">
  <img src="https://github.com/gdcc/easyDataverse/blob/main/static/logo.png" width=300 alt="EasyDataverse"></br>
  <img src="https://img.shields.io/badge/EasyDataverse-0.3.8-blue" alt="v0.3.6">
  <img src="https://github.com/gdcc/easyDataverse/actions/workflows/build.yaml/badge.svg" alt="Build Badge">
</a>
</h1>
<p align="center"> 
EasyDataverse is a Python libary used to interface Dataverse installations and generate Python code compatible to a metadatablock configuration given at a Dataverse installation. In addtion, EasyDataverse allows you to export and import datasets to and from various data formats.</p>

###  Features

- **Metadataconfig compliant** classes for flexible Dataset creation.
- **Upload and download** of files and directories to and from Dataverse installations.
- **Export and import** of datasets to various formats (JSON, YAML, XML and HDF5).
- **Fetch datasets** from any Dataverse installation into an object oriented structure ready to be integrated.

## ⚡️ Quick start
Get started with EasyDataverse by running the following command 

```
# Using PyPI
python -m pip install easyDataverse
```

Or build by source

```
git clone https://github.com/gdcc/easyDataverse.git
cd easyDataverse
python setup.py install
```

## ⚙️ Quickstart


### Dataset creation

EasyDataverse is capable of connecting to a given Dataverse installation and fetch all metadata fields and their properties. This allows you to create a dataset object with all the metadata fields and their properties given at the Dataverse installation.

```python
from easyDataverse import Dataverse

# Connect to a Dataverse installation
dataverse = Dataverse(
  server_url="https://demo.dataverse.org",
  api_token=MY_API_TOKEN,
)

# Intiialize a dataset
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

### Dataset download

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
  
)

print(dataset) # Displays the content 
```

## 📖 Documentation and more examples

🚧 Under construction 🚧

## ✍️ Authors

- Jan Range (EXC2075 SimTech, University of Stuttgart)

## ⚠️ License

`EasyDataverse` is free and open-source software licensed under the [MIT License](). 
