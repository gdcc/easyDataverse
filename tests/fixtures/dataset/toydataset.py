from enum import Enum
from typing import Optional, List
from easyDataverse.base import DataverseBase
from pydantic import Field


class SomeEnum(Enum):
    enum = "enum"


class CompoundField(DataverseBase):
    bar: Optional[str] = Field(
        None,
        description="Another primitive field",
        multiple=False,
        typeClass="primitive",
        typeName="fooCompoundField",
    )


class ToyDataset(DataverseBase):
    foo: Optional[str] = Field(
        None,
        description="Some primitive field",
        multiple=False,
        typeClass="primitive",
        typeName="fooField",
    )

    compound: List[CompoundField] = Field(
        default_factory=list,
        description="Some compound field",
        multiple=False,
        typeClass="compound",
        typeName="fooCompound",
    )

    some_enum: SomeEnum = Field(
        ...,
        description="Some enum field",
        multiple=False,
        typeClass="controlledVocabulary",
        typeName="fooEnum",
    )

    def add_compound(self, bar):
        self.compound.append(CompoundField(bar=bar))

    _metadatablock_name: Optional[str] = "testblock"
