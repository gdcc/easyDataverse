import pytest

from easyDataverse import Dataset
from easyDataverse.core.base import DataverseBase

from tests.fixtures.dataset.toydataset import ToyDataset, SomeEnum
from tests.fixtures.dataset.invalidclass import InvalidBlock, AnotherEnum


@pytest.fixture
def metadatablock():
    """Simple artificial metadatablock."""

    block = ToyDataset(foo="foo", some_enum=SomeEnum.enum)
    block.add_compound("bar")

    return block


@pytest.fixture
def toy_dataset():
    """Simple artificial metadatablock."""

    # Set up the metadatablock
    block = ToyDataset(foo="foo", some_enum=SomeEnum.enum)
    block.add_compound("bar")

    # Add to dataset
    dataset = Dataset()
    dataset.add_metadatablock(block)

    return dataset


@pytest.fixture
def invalid_block():
    """Simple artificial class that looks similar to a valid block, but has invalid parent"""

    block = InvalidBlock(foo="foo", some_enum=AnotherEnum.enum_field)
    block.add_compound("bar")

    return block


@pytest.fixture
def dataverse_json():
    """Expected JSON output when passed to pyDataverse"""

    return open("./tests/fixtures/dataset/dataverse_json_output.json").read()


@pytest.fixture
def yaml_input():
    """YAML file used to initialize a dataset"""

    return open("./tests/fixtures/yaml_output.yaml").read()


@pytest.fixture
def dataverse_base_class():
    """Sets up a dummy class to test the base class"""

    class Test(DataverseBase):
        foo: str
        bar: str

    return Test


@pytest.fixture
def metadatablock_json_schema():
    """Sets up a metadatablock json schema"""

    return open("./tests/fixtures/dataversebase/toydataset.schema.json").read()
