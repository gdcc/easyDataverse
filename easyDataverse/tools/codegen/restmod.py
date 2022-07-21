import importlib
import glob
import os
import inspect

from pathlib import Path
from jinja2 import Template
from importlib import resources as pkg_resources

from easyDataverse.tools.codegen import templates as jinja_templates
from easyDataverse.tools.utils import get_class


def generate_rest_api_code(
    metadatablock_loc: str, lib_name: str, lib_path: str
) -> None:
    """Generates code that will be used to build a REST interface."""

    endpoints, imports = [], []
    # sys.path.append(metadatablock_loc)

    # Initialize Jinja templates
    import_template = Template(
        pkg_resources.read_text(jinja_templates, "rest_imports_template.jinja2")
    )
    create_template = Template(
        pkg_resources.read_text(jinja_templates, "rest_create_template.jinja2")
    )

    for path in glob.glob(os.path.join(metadatablock_loc, "*.py")):

        # Get module name
        module_name = Path(path).stem

        if module_name == "__init__":
            continue

        # Get the class name
        class_name, _ = get_class(module_name, path)

        endpoints.append(
            create_template.render(module_name=module_name, class_name=class_name)
        )

        # Add infos to imports
        imports.append({"module": module_name, "class": class_name})

    # Finally, write REST API to file
    out_path = os.path.join(lib_path, f"{lib_name.lower()}_server.py")
    with open(out_path, "w") as f:
        f.write(import_template.render(imports=imports, lib_name="pyDaRUS"))
        f.write("\n\n".join(endpoints))


def get_class_name(module_name: str, module_path: str) -> str:
    """Retrieves the correct class name of a module"""

    # Import the module
    module = importlib.import_module(module_name, module_path)

    for class_name, _ in inspect.getmembers(module, inspect.isclass):
        if class_name.lower() == module_name.lower():
            return class_name

    raise ModuleNotFoundError(
        f"Couldnt find corresponding class {module_name} in {module_path}."
    )
