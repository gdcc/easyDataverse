import yaml
from typing import Tuple


class YAMLDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YAMLDumper, self).increase_indent(flow, False)

def extract_major_minor(version: str) -> Tuple[int, int]:
    """Extracts the major and minor version numbers from a Dataverse version string.
    
    Args:
        version: A string representing the Dataverse version, e.g., "6.4.0" or "v6.4.0".
    """
    try:
        major, minor, *_ = version.split(".")
        major = "".join(filter(str.isdigit, major))
        minor = "".join(filter(str.isdigit, minor))
        return int(major), int(minor)
    except ValueError:
        raise ValueError(f"Version '{version}' is not a valid Dataverse version.")