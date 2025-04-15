import datetime
import json
import os
from pydantic.fields import FieldInfo
from typing_extensions import Set
from pydantic_core import Url
import rich
import yaml
import xmltodict

from anytree import Node, RenderTree, ContRoundStyle
from enum import Enum
from pydantic import BaseModel, ConfigDict, PrivateAttr
from typing import Any, Dict, List, Optional, get_args, get_origin

from easyDataverse.utils import YAMLDumper


class DataverseBase(BaseModel):
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    _changed: Set = PrivateAttr(default_factory=set)
    _new: bool = PrivateAttr(default=True)

    # ! Overloads
    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.model_fields:
            self._changed.add(name)

        return super().__setattr__(name, value)

    @classmethod
    def from_json_string(cls, json_string: str):
        """Initializes an object from a JSON file"""

        return cls.model_validate(json.loads(json_string))

    @classmethod
    def from_json_file(cls, file_path: str):
        """Initializes an object from a JSON file"""

        with open(file_path, "r") as f:
            return cls.model_validate(json.load(f))

    @classmethod
    def from_yaml_string(cls, yaml_string: str):
        """Initializes an object from a YAML string"""

        return cls.model_validate(yaml.safe_load(yaml_string))

    @classmethod
    def from_yaml_file(cls, file_path: str):
        """Initializes an object from a YAML string"""

        with open(file_path, "r") as f:
            return cls.model_validate(yaml.safe_load(f))

    def json(self, indent: int = 2, **kwargs) -> str:
        """Returns a JSON representation of the dataverse object."""

        # Read the JSON to filter empty compounds
        json_obj = json.loads(
            super().model_dump_json(
                exclude_none=True,
                indent=indent,
                by_alias=True,
                **kwargs,
            )
        )

        return json.dumps(
            {key: value for key, value in json_obj.items() if value != []},
            indent=indent,
            default=str,
        )

    def yaml(self, exclude_none: bool = True, **kwargs) -> str:
        """Returns a YAML representation of the dataverse object"""

        yaml_obj = self.dict(exclude_none=exclude_none, **kwargs)

        return yaml.safe_dump(yaml_obj)

    def dict(self, **dictkwargs) -> Dict:
        """Returns a dictionary representation of the dataverse object."""

        # Get the dictionary function from pyDantic
        fields = super().model_dump(**dictkwargs, by_alias=True)

        return {
            key: value for key, value in fields.items() if value != {} and value != []
        }

    def xml(self, **dictkwargs) -> str:
        """Returns an XML representation of the dataverse object."""

        # Turn all fields to camel case
        fields = self._keys_to_camel({self.__class__.__name__: self.dict(**dictkwargs)})

        return xmltodict.unparse(fields, pretty=True, indent="    ")

    def _keys_to_camel(self, dictionary: Dict):
        nu_dict = {}
        for key in dictionary.keys():
            if isinstance(dictionary[key], dict):
                nu_dict[self._snake_to_camel(key)] = self._keys_to_camel(
                    dictionary[key]
                )
            else:
                nu_dict[self._snake_to_camel(key)] = dictionary[key]
        return nu_dict

    @staticmethod
    def _snake_to_camel(word: str) -> str:
        return "".join(x.capitalize() or "_" for x in word.split("_"))

    def dataverse_dict(self) -> Dict:
        """Converts a metadatablock object model to the appropriate dataverse JSON format"""

        # Get properties and init json_obj
        json_obj = {}

        for attr, field in self.model_fields.items():
            if any(name in attr for name in ["add_", "_metadatablock_name"]):
                # Only necessary for blind fetch
                continue

            # Fetch the value of the attribute
            properties = field.json_schema_extra
            value = getattr(self, attr)

            if self.is_empty(value):
                # Guard clause to catch empty compounds
                continue

            # Process compounds
            if properties["typeClass"] == "compound":
                if isinstance(value, list):
                    value = [field.dataverse_dict() for field in value]
                else:
                    value = value.dataverse_dict()

            if isinstance(value, list):
                # TODO Refactor to separate check
                if all(isinstance(val, Enum) for val in value):
                    value = [val.value for val in value]
            elif isinstance(value, dict):
                pass
            elif isinstance(value, (datetime.date, datetime.datetime)):
                value = value.strftime("%Y-%m-%d")
            elif isinstance(value, Url):
                value = str(value)
            else:
                value = str(value)

            json_obj.update(
                {
                    properties["typeName"]: {
                        "multiple": properties["multiple"],
                        "typeClass": properties["typeClass"],
                        "typeName": properties["typeName"],
                        "value": value,
                    }
                }
            )

        if hasattr(self, "_metadatablock_name") and list(json_obj.values()):
            return {
                getattr(self, "_metadatablock_name"): {
                    "fields": list(json_obj.values())
                }
            }
        else:
            return json_obj

    def to_dataverse_json(self, indent: int = 2) -> str:
        """Returns a JSON formatted representation of the dataverse object."""
        return json.dumps(self.dataverse_dict(), indent=indent)

    def extract_changed(self) -> List[Dict]:
        """Extracts the changed fields from the object"""

        changed_fields = []

        self._add_changed_multiples()

        for name in self._changed:
            field = self.model_fields[name]

            if self._is_compound(field) and self._is_multiple(field):
                value = self._process_multiple_compound(getattr(self, name))
            elif self._is_compound(field):
                value = self._process_single_compound(getattr(self, name))
            else:
                value = getattr(self, name)

            if value:
                changed_fields.append(self._wrap_changed(field, value))

        return changed_fields

    def _add_changed_multiples(self):
        """Checks whether a compound has multiple changed fields"""

        for name, field in self.model_fields.items():
            if not self._is_compound(field):
                continue
            if not self._is_multiple(field):
                continue

            has_changed = any(
                compound._changed or compound._new
                for compound in getattr(self, name)
            )

            if has_changed:
                self._changed.add(name)

    def _process_multiple_compound(self, compounds) -> List[Dict]:
        """Processes multiple compounds"""

        return [compound.dataverse_dict() for compound in compounds]

    def _process_single_compound(self, compound) -> Dict:
        """Processes a single compound"""

        if not compound._changed:
            return {}

        return compound.dataverse_dict()

    def _is_compound(self, field_info: FieldInfo):
        """Checks whether a field is a compound"""

        return field_info.json_schema_extra["typeClass"] == "compound"  # type: ignore

    def _is_multiple(self, field):
        """Checks whether a field is multiple"""

        return field.json_schema_extra["multiple"]

    def _wrap_changed(self, field: FieldInfo, value: Any):
        """Wraps the changed field with type name"""

        assert "typeName" in field.json_schema_extra  # type: ignore

        return {
            "typeName": field.json_schema_extra["typeName"],  # type: ignore
            "value": value,
        }

    def _set_new_prop(self, value: bool):
        """Sets the new property of the object"""

        self._new = value

        for attr, field in self.model_fields.items():
            if not field.json_schema_extra["typeClass"] == "compound":
                continue

            if field.json_schema_extra["multiple"]:
                for compound in getattr(self, attr):
                    compound._set_new_prop(value)
            else:
                getattr(self, attr)._set_new_prop(value)

    @staticmethod
    def is_empty(value):
        """Checks whether a given value is None or empty"""

        if value is None:
            return True
        elif value == []:
            return True
        elif hasattr(value, "model_fields") and value.dict(exclude_none=True) == {}:
            return True

        return False

    @classmethod
    def info(
        cls,
        schema: bool = True,
        functions: bool = True,
    ) -> None:
        """Displays the schema tree described within this class"""

        rich.print(
            RenderTree(
                style=ContRoundStyle(),
                node=cls._create_tree(
                    functions=functions,
                    schema=schema,
                    printing=True,
                ),
            ).by_attr("name")
        )

    @classmethod
    def _create_tree(
        cls,
        schema: bool = True,
        functions: bool = False,
        parent: Optional[Node] = None,
        printing: bool = False,
    ) -> Node:
        """Creates a tree from the given metadatablock/compound"""

        if printing:
            attribute = "[bold]{0}[/bold]: [italic]{1}[/italic]"
            block = "[bold cyan2]{0}[/bold cyan2]"
        else:
            attribute = "{0}"
            block = "{0}"

        if parent is None:
            root = Node(block.format(cls.__name__))
            root.parent = parent
        else:
            root = parent

        if schema:
            for name, field in cls.model_fields.items():
                if get_args(field.annotation):
                    dtype = get_args(field.annotation)[0]
                else:
                    dtype = field.annotation

                try:
                    dtype_name = dtype.__name__
                except AttributeError:
                    dtype_name = dtype.__class__.__name__

                if dtype_name == "Annotated":
                    dtype_name = dtype.__origin__.__name__

                node = Node(attribute.format(name, dtype_name))
                node.typeName = field.json_schema_extra["typeName"]
                node.typeClass = field.json_schema_extra["typeClass"]
                node.parent = root

                if hasattr(dtype, "model_fields"):
                    dtype._create_tree(
                        parent=node,
                        functions=functions,
                        schema=schema,
                    )

        add_funs = [key for key in cls.__dict__.keys() if key.startswith("add_")]
        if functions and add_funs:
            function_root = Node("[bold italic]Add Functions[/bold italic]")
            function_root.parent = root

            for key in cls.__dict__.keys():
                if not key.startswith("add_"):
                    continue

                node = Node(key)
                node.parent = function_root

        return root

    # ! Template exporter
    @classmethod
    def export_template(
        cls,
        path: str,
        format: str = "json",
    ):
        assert format in ["json", "yaml"], "Format must be either 'json' or 'yaml'"

        example = cls._construct_example_ds(cls)

        if format == "json":
            fpath = os.path.join(path, f"{cls.__name__.lower()}_template.json")
            with open(fpath, "w") as f:
                json.dump(example, f, indent=2)
        elif format == "yaml":
            fpath = os.path.join(path, f"{cls.__name__}_template.yaml")
            with open(fpath, "w") as f:
                yaml.dump(
                    data=example,
                    stream=f,
                    Dumper=YAMLDumper,
                    default_flow_style=False,
                    sort_keys=False,
                )

        rich.print(f"💽 [bold]Template exported to [green]{fpath}[/green][/bold]")

    @classmethod
    def _construct_example_ds(cls, block):
        """
        Constructs an example data structure based on the given block.

        Args:
            block (DataverseBase): The block object to construct the example data structure from.

        Returns:
            dict: The example data structure.

        """

        example_ds = {}

        for field in block.model_fields.values():
            annot = field.annotation
            dtype = [t for t in get_args(annot) if t is not type(None)][0]
            alias = field.alias

            is_multiple = get_origin(annot) is list
            is_complex = hasattr(dtype, "model_fields")

            if dtype.__name__ == "Annotated":
                dtype_name = "URL"
            else:
                dtype_name = dtype.__name__

            if is_complex:
                sub_example = cls._construct_example_ds(dtype)
                if is_multiple:
                    example_ds[alias] = [sub_example]
                else:
                    example_ds[alias] = sub_example
            else:
                if is_multiple:
                    example_ds[alias] = [f"Enter data of type {dtype_name}"]
                else:
                    example_ds[alias] = f"Enter data of type {dtype_name}"

        return example_ds
