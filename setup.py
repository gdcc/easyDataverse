import setuptools
from setuptools import setup

__VERSION__ = "0.3.6"

setup(
    name="easyDataverse",
    version=__VERSION__,
    author="Jan Range",
    author_email="jan.range@simtech.uni-stuttgart.de",
    license="MIT License",
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points={"console_scripts": ["dataverse=easyDataverse.cli:main"]},
    install_requires=[
        "pydantic==1.9.0",
        "jinja2",
        "pydataverse",
        "pandas",
        "datamodel_code_generator",
        "pyaml",
        "coloredlogs",
        "xmltodict",
        "tqdm",
        "deepdish",
        "h5py",
        "typer",
        "python-forge",
    ],
    extras_require={"test": ["pytest-cov"]},
)
