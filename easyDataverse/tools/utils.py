import importlib
import inspect
import yaml

from typing import Callable, Tuple

class YAMLDumper(yaml.Dumper):

    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)

def get_class(module_name: str, module_path: str) -> Tuple[str, Callable]:
    """Retrieves the correct class name of a module"""

    # Import the module
    module = importlib.import_module(module_name, module_path)
    
    for class_name, class_def in inspect.getmembers(module, inspect.isclass):
        if class_name.lower() == module_name.lower().split(".")[-1]:
            return class_name, class_def

    raise ModuleNotFoundError(
        f"Couldnt find corresponding class {module_name} in {module_path}."
    )

