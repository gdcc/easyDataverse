import re
import pandas as pd

from typing import List

# Typing that is used to infer proper types
type_mapping = {
    "text": "string",
    "url": "string",
    "float": "number",  # TODO Float not parsed as float rather as number
    "integer": "integer",
    "int": "integer",
    "textbox": "string",
    "date": "string",
    "email": "string",
}


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def spaced_to_snake(name) -> str:
    # Clean the title
    name = re.sub(r"-|\?", "_", name)
    name = name.replace(r"/", " ")

    return "_".join([word.lower() for word in name.replace("-", " ").split(" ")])


def split_metadatablock(metadatablock: pd.DataFrame):
    """Splits a Metadatablock to the fields and controlled vocabularies if given."""

    try:
        split_index = metadatablock.index[
            metadatablock["#datasetField"] == "#controlledVocabulary"
        ].values[0]

        # Get fields and vocabulary
        fields = metadatablock.iloc[0:split_index]
        controlled_vocab = metadatablock.iloc[split_index::]

        # Set top row as columns for controlled vocab
        controlled_vocab.columns = controlled_vocab.iloc[0]
        controlled_vocab = controlled_vocab[1::]

        return fields, controlled_vocab

    except IndexError:
        # No controlled vocabularies found
        return metadatablock, None


def generate_JSON_schema(
    fields: pd.DataFrame, metadatablock_name: str, controlled_vocab: pd.DataFrame
):
    """Sorts Fields by compounds or single fields"""

    # Initialize compound and single field dictionaries
    properties = {}
    definitions = {}
    required = []

    # Get all parent fields
    parents = set(fields.parent)

    for parent in parents:
        if str(parent) == "nan":
            # Process any primitive field to JSON
            primitives = fields[
                (fields["parent"].isna()) & (fields["fieldType"] != "none")
            ]
            property = fetch_fields(
                primitives.to_dict(orient="records"), controlled_vocab
            )

        else:
            # Process data to a compound JSON
            property, compound_name, definition = construct_compound(
                parent, fields, controlled_vocab, metadatablock_name
            )

            # Add to Schema
            required.append(compound_name)
            definitions.update(definition)

        properties.update(property)

    # Add property to identify class as a metadatablock
    properties.update(
        {"_metadatablock_name": {"default": metadatablock_name, "type": "string"}}
    )

    return properties, definitions, required


def construct_compound(
    parent: str,
    fields: pd.DataFrame,
    controlled_vocab: pd.DataFrame,
    metadatablock_name: str,
):
    """Returns the JSON schema properties as well as definitions"""

    # Get Compound meta information
    compound_row = fields[fields.name == parent]
    compound_dict = compound_row.to_dict(orient="records")[0]
    compound_name = spaced_to_snake(compound_dict["title"])

    if compound_name == spaced_to_snake(metadatablock_name):
        compound_name = compound_name + "_data"

    # Fetch all fields corresponding to the compound
    fields = fields[fields.parent == parent].to_dict(orient="records")

    # Get Compound schema for property
    object_props = {
        compound_name: {
            "typeName": compound_dict["name"],
            "type": "array",
            "typeClass": "compound",
            "multiple": bool(compound_dict["allowmultiples"]),
            "description": compound_dict["description"],
            "items": {"$ref": f"#/definitions/{compound_name}"},
        }
    }

    fields = fetch_fields(fields, controlled_vocab)

    return object_props, compound_name, {compound_name: {"properties": fields}}


def fetch_fields(fields: List[dict], controlled_vocab: pd.DataFrame):
    """Retrieves and parses fields given in a metadatablock"""

    # Initialize field dictionary
    field_defs = {}

    for field in fields:
        field_defs.update(parse_field(field, controlled_vocab))

    return field_defs


def parse_field(field: dict, controlled_vocab: pd.DataFrame):
    """Parses a field to the appropriate JSON schema and retrieves controlled_vocabs"""

    # Set defaults
    field_name = spaced_to_snake(field["title"])
    type_class = "primitive"
    allowed_vals = None

    if field["allowmultiples"]:
        data_type = "array"
    else:
        data_type = type_mapping[field["fieldType"]]

    if field["allowControlledVocabulary"] and controlled_vocab is not None:
        type_class = "controlledVocabulary"
        allowed_vals = get_controlled_vocabs(field["name"], controlled_vocab)

    field_def = {
        "typeName": field["name"],
        "typeClass": type_class,
        "multiple": field["allowmultiples"],
        "type": data_type,
        "description": field["description"],
    }

    if allowed_vals:
        field_def["enum"] = allowed_vals

    if field_name == "subject" and controlled_vocab is not None:
        # TODO find elegant way to handle special fields
        field_def = {
            "typeName": field["name"],
            "typeClass": type_class,
            "multiple": field["allowmultiples"],
            "type": "array",
            "items": {"type": "string", "enum": allowed_vals},
            "description": field["description"],
        }

    return {field_name: field_def}


def get_controlled_vocabs(name: str, controlled_vocab: pd.DataFrame):
    """Retrieves the possible values for a controlled vocabulary"""

    cv_fields = controlled_vocab[controlled_vocab["DatasetField"] == name]
    return cv_fields["Value"].tolist()
