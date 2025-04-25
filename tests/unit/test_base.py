import pytest

from typing import List, Optional
from pydantic import Field
from easyDataverse.base import DataverseBase


class TestBase:
    @pytest.mark.unit
    def test_template(self):
        # Arrange
        class Child(DataverseBase):
            bar: Optional[str] = Field(
                default=None,
                alias="Foo",
            )

        class Test(DataverseBase):
            foo: Optional[str] = Field(
                default=None,
                alias="Foo",
            )
            nested: List[Child] = Field(
                default_factory=list,
                alias="Nested",
            )

        # Act
        example = Test._construct_example_ds(Test)

        # Assert
        expected = {
            "Foo": "Enter data of type str",
            "Nested": [{"Foo": "Enter data of type str"}],
        }

        assert example == expected, "Example data is not as expected"
