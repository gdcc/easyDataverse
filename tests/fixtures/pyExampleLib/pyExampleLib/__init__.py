import os

from easyDataverse import Dataset, ProgrammingLanguage
from pyExampleLib.metadatablocks import ToyDataset

# Add the lib_name to the operating systems env
os.environ["EASYDATAVERSE_LIB_NAME"] = "pyExampleLib"