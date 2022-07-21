import importlib
import shutil
import sys

from easyDataverse.tools.codegen.generator import generate_python_api


def _get_module(name: str, loc: str):
    """Fetches a module from a loc"""

    spec = importlib.util.spec_from_file_location(name, loc)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


class TestCodegen:
    def test_codegen(self):
        """Tests whether the dummy TSV file is converted to code correctly"""

        # Generate the API
        generate_python_api(
            path="./tests/fixtures/blocks",
            out="./tests/generator_test",
            name="pySomeTest",
        )

        # Import the metadatablock
        block = _get_module(
            "toyDataset",
            "./tests/generator_test/pySomeTest/pySomeTest/metadatablocks/toyDataset.py",
        )

        toydata = block.ToyDataset(foo="foo", some_enum=block.SomeEnum.enum)
        toydata.add_compound(bar="bar")
