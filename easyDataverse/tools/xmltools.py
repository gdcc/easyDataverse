from typing import Any, Tuple
from lxml import objectify, etree

from sdRDM.tools.utils import snake_to_camel


class XMLWriter:

    @classmethod
    def to_xml(
        cls,
        root_name: str,
        values: dict,
        props: dict,
        to_string: bool = True
    ) -> objectify.ObjectifiedElement:
        """Writes the object data model to XML"""

        # Initialize attrib/element mapping
        attributes = {}
        elements = []

        # Collect attributes and elements
        for name, value in values.items():
            if name.startswith("__"):
                continue

            # Get xml class and data type
            xml, data_type = cls._get_xml_specs(props[name])

            # Treat all those cases
            if xml == "attribute":
                attributes.update({name: str(value)})

            elif xml == "element":
                elements.append(cls._make_element(
                    name, value, data_type
                ))

        # Construct resulting element
        root = objectify.Element(
            root_name,
            **attributes
        )

        root.extend(elements)

        # Some cleanups
        objectify.deannotate(root)
        etree.cleanup_namespaces(root)

        if to_string:
            xml_string = etree.tostring(
                root,
                pretty_print=True,
                xml_declaration=True
            )

            return xml_string.decode()

        return root

    @staticmethod
    def _get_xml_specs(properties: dict) -> Tuple[str, str]:
        """Extracts the xml classification and type"""

        def infer_property(key: str):
            mapping = {
                "xml": "element",  # Make it an element if not otherwise stated
                "type": "object"
            }

            try:
                return properties[key]
            except KeyError:
                return mapping[key]

        return (
            infer_property("xml"),
            infer_property("type")
        )

    @staticmethod
    def _make_element(name: str, value: Any, data_type: str):
        """Creates elements based on their type and recursively
           generated elements from other classes"""

        name = snake_to_camel(name)

        if data_type not in ["object", "array"]:
            # Primitive types
            elem = etree.Element(name)
            elem.text = str(value)
            return elem

        # Process nested types
        elem = objectify.Element(name)

        if data_type == "object":
            elem.extend([value.to_xml(to_string=False)])
        elif data_type == "array":
            elem.extend([entry.to_xml(to_string=False) for entry in value])
        else:
            raise TypeError(f"Data type of {data_type} is unknown.")

        return elem
