import argparse
import os
import glob
import yaml
import json
import logging
import coloredlogs


from jinja2 import Template
from typing import Callable
from importlib import resources as pkg_resources

from easyDataverse.tools.utils import YAMLDumper
from easyDataverse.tools.codegen import templates as jinja_templates
from easyDataverse.tools.codegen.clsmod import generate_metadatablock_code
from easyDataverse.tools.codegen.restmod import generate_rest_api_code
from easyDataverse.tools.codegen.filehandling import (
    create_init_line_metadatblock,
    create_init_line_library,
    generate_template,
)


def generate_python_api(path: str, out: str, name: str, log_state: str = "INFO"):

    # Logger
    global logger
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=log_state)

    # Process args
    project_path = os.path.join(out, name)
    lib_path = os.path.join(out, name, name)
    metadatablock_loc = os.path.join(out, name, name, "metadatablocks")
    schema_loc = os.path.join(out, name, name, "metadatablocks", "schemas")
    template_loc = os.path.join(out, name, name, "templates")

    # Create dir structure
    os.makedirs(schema_loc, exist_ok=True)
    os.makedirs(os.path.join(template_loc, "yaml"), exist_ok=True)
    os.makedirs(os.path.join(template_loc, "json"), exist_ok=True)

    # Create metadatablock code
    metadatablocks(path, metadatablock_loc, schema_loc, lib_path, name)

    # Create setup file
    setup(name, project_path)

    # Create templates
    templates(metadatablock_loc, template_loc)

    # Generate REST API
    generate_rest_api_code(metadatablock_loc, name, lib_path)

    logger.info(f"Created REST-API for {name}")

    # Generate Dockerfile
    docker_template = Template(
        pkg_resources.read_text(jinja_templates, "dockerfile.jinja2")
    )

    docker_out = os.path.join(project_path, "Dockerfile")
    with open(docker_out, "w") as f:
        f.write(docker_template.render(lib_name=name))

    logger.info(f"Created library {name} in {os.path.abspath(project_path)}")


def metadatablocks(
    path: str, metadatablock_loc: str, schema_loc: str, lib_loc: str, lib_name: str
) -> None:
    """Generates the metadatablock relevant files for the API."""

    # Generate code for the metadatablocks
    for block_path in glob.glob(os.path.join(path, "*.tsv")):
        generate_metadatablock_code(block_path, metadatablock_loc, schema_loc)
        logger.info(f"Generated metadatablock code for {block_path}")

    # Get the correspding module names form the files
    module_search = os.path.join(metadatablock_loc, "*.py")

    # Write __init__ files
    write_imports(
        module_search,
        lib_loc,
        "library_init.jinja2",
        create_init_line_library,
        lib_name,
    )

    write_imports(
        module_search,
        metadatablock_loc,
        "metadatablock_init.jinja2",
        create_init_line_metadatblock,
        lib_name,
    )


def write_imports(
    module_search: str, path: str, template_path: str, fun: Callable, lib_name: str
):
    """Extract module names, creates imports via a function and writes them to a path"""

    imports = [
        fun(module, lib_name)
        for module in glob.glob(module_search)
        if "__init__" not in module
    ]

    with open(os.path.join(path, "__init__.py"), "w") as f:
        template = Template(pkg_resources.read_text(jinja_templates, template_path))

        f.write(template.render(imports=imports, lib_name=lib_name))


def setup(name: str, project_path: str) -> None:
    """Generates the relevant setup file to install the API."""

    requirements = [
        "easyDataverse",
        "fastapi",
        "uvicorn",
        "pydantic",
        "jinja2",
        "pyDataverse",
        "pandas",
        "pyaml",
        "typer",
    ]

    # Initialize Jinja template
    template = Template(pkg_resources.read_text(jinja_templates, "setup.jinja2"))

    # Write to the API directory
    setup_path = os.path.join(project_path, "setup.py")
    with open(setup_path, "w") as f:
        f.write(template.render(name=name, requirements=requirements))

    # Write requirements.txt
    requirements_path = os.path.join(project_path, "requirements.txt")
    with open(requirements_path, "w") as f:
        for req in requirements:
            f.write(req + "\n")


def templates(metadatablock_loc: str, template_loc: str) -> None:
    """Generates templates which can then be used for mapping from file formats to Dataverse."""

    # Get the correspding module names form the files
    module_search = os.path.join(metadatablock_loc, "*.py")

    for module in glob.glob(module_search):

        if "__init__" in module:
            continue

        # Generate empty data model
        block_name, data_model = generate_template(module)

        # Write template to YAML
        with open(os.path.join(template_loc, "yaml", f"{block_name}.yaml"), "w") as f:
            yaml.dump(
                data_model,
                f,
                sort_keys=False,
                default_flow_style=False,
                Dumper=YAMLDumper,
            )

        # Write template to JSON
        with open(os.path.join(template_loc, "json", f"{block_name}.json"), "w") as f:
            json.dump(data_model, f, indent=2, sort_keys=False)

        logger.info(f"Created template for {block_name}.")
