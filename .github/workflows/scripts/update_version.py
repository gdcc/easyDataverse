"""
This script will update version in:

    - README.MD badge
    - __version__ in library

"""

import re

# Setup parsing
setup_file = open("setup.py").readlines()
version_line = list(
    filter(lambda line: bool(re.match(r"__VERSION__\s?=", line)), setup_file)
)[0]

# Get new version
version_pattern = r"(\d.\d*.\d*)"
version = re.findall(version_pattern, version_line)[0]

# Process readme file
readme = open("Readme.md", "r").read()
new_badge = f"badge/EasyDataverse-{version}-blue"
with open("Readme.md", "w") as f:
    nu_readme = re.sub(r"badge/EasyDataverse-\d.\d*.\d*-blue", new_badge, readme)
    f.write(nu_readme)

# Process __init__ file
init_file = open("easyDataverse/__init__.py", "r").read()
new_version = f'__version__ = "{version}"'

with open("easyDataverse/__init__.py", "w") as f:
    nu_init_file = re.sub(r"__version__\s?=\s?\"\d.\d*.\d*\"", new_version, init_file)
    f.write(nu_init_file)
