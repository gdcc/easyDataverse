import setuptools
from setuptools import setup

setup(
    name='pySomeTest',
    version='1.0.0',
    author='easyDataverse',
    license='MIT License',
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": ["pysometest=easyDataverse.cli:main"]
    },
    install_requires=[
        'easyDataverse',
        'fastapi',
        'uvicorn',
        'pydantic',
        'jinja2',
        'pyDataverse',
        'pandas',
        'pyaml',
        'typer',
    ]
)