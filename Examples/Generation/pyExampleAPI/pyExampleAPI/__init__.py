import os

from easyDataverse import Dataset, ProgrammingLanguage
from pyExampleAPI.metadatablocks import Astrophysics
from pyExampleAPI.metadatablocks import Citation
from pyExampleAPI.metadatablocks import Journal
from pyExampleAPI.metadatablocks import Socialscience
from pyExampleAPI.metadatablocks import CodeMeta
from pyExampleAPI.metadatablocks import Biomedical
from pyExampleAPI.metadatablocks import Geospatial
from pyExampleAPI.metadatablocks import Archive
from pyExampleAPI.metadatablocks import Privacy

# Add the lib_name to the operating systems env
os.environ["EASYDATAVERSE_LIB_NAME"] = "pyExampleAPI"