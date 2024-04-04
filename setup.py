import setuptools
from setuptools import setup

__VERSION__ = "0.4.0"

setup(
    name="easyDataverse",
    version=__VERSION__,
    author="Jan Range",
    author_email="jan.range@simtech.uni-stuttgart.de",
    license="MIT License",
    packages=setuptools.find_packages(),
    package_data={"": ["*.jinja2"]},
    include_package_data=True,
    entry_points={"console_scripts": ["dataverse=easyDataverse.cli:main"]},
    install_requires=[
        "pydantic",
        "jinja2",
        "pydataverse",
        "pyaml",
        "xmltodict",
        "typer",
        "python-forge",
        "anytree",
        "dotted-dict==1.1.3",
        "python-forge==18.6.0",
        "rich",
        "nob",
        "nest_asyncio",
        "aiohttp",
        "aiodns",
        "dvuploader",
        "email_validator",
    ],
    extras_require={"test": ["pytest-cov"]},
)
