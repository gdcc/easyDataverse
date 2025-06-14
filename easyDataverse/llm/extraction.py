"""
LLM-powered metadata extraction module for Dataverse.

This module provides functionality to extract structured metadata from text content
using OpenAI's language models with structured output parsing. It supports various
tools including web search and Dataverse MCP integration.
"""

from enum import Enum
import re
from typing import (
    IO,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    Union,
    get_args,
)
from openai import OpenAI
from openai.types.responses import ResponseInputParam, ResponseCompletedEvent
from openai.types.responses.tool_param import ParseableToolParam
from openai.types.file_object import FileObject
from pydantic import BaseModel, Field, create_model, model_validator
from rich.console import Console
from rich.status import Status

from easyDataverse.base import DataverseBase

# Initialize rich console
console = Console()

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]
USER_DATA_EXTENSIONS = [".pdf"]
ENUM_THRESHOLD = 20
DATAVERSE_MCP_URL = "https://mcp.dataverse.org/sse"

DEFAULT_UNCHECKED_PROMPT = """
You are a metadata extraction assistant. Extract structured metadata from the provided text and return ONLY a JSON object.

CRITICAL INSTRUCTIONS:
- Your response must be ONLY valid JSON - no explanatory text, no markdown, no additional content
- Extract only information that is explicitly stated or clearly implied in the text
- Do not make assumptions or add information not present in the source
- If information is missing or unclear, omit those fields from the JSON
- Return the JSON object directly without any wrapper text
- If the web search is enabled, use it to retrieve the most relevant information

Schema to follow:
{schema}

Return only the JSON object:
"""

DEFAULT_PRUNE_PROMPT = """
You are an expert metadata extraction specialist. Analyze the available fields and identify which ones are relevant for extracting metadata from the provided text.

Your task:
1. Select fields that contain information explicitly stated in the text
2. Include fields for information that can be reasonably inferred from context
3. Consider implicit metadata that domain experts would recognize
4. Include fields that are not explicitly stated but are implied by the content and can be reasonably inferred by an LLM

Focus on completeness while maintaining accuracy. Return only fields that have a reasonable chance of being populated from the given content.
"""

PRUNE_TEMPLATE = """
The following fields and their descriptions are available:

{fields}

The following text is the content to extract metadata from:

{content}
"""

# Improved JSON refinement prompt
JSON_REFINEMENT_PROMPT = """
You are given rough JSON extracted metadata. Your task is to:
1. Clean and validate the JSON structure
2. Ensure all fields match the expected schema format
3. Fix any formatting issues or type mismatches
4. Preserve all extracted information
5. Return only valid JSON - no explanatory text

The input contains extracted metadata. Clean and validate it according to the schema.
"""


class ExtractionConfig(BaseModel):
    """Configuration class for metadata extraction settings.

    This class defines all the parameters needed to configure the metadata extraction
    process, including model selection, temperature settings, and feature flags.

    Attributes:
        extraction_model (str): The OpenAI model to use for initial metadata extraction.
            Defaults to "gpt-4.1".
        refinement_model (Optional[str]): The model to use for refining extracted metadata.
            If None, uses the same model as extraction_model.
        prune_model (Optional[str]): The model to use for schema pruning.
            If None, uses the same model as extraction_model.
        temperature (Optional[float]): Temperature setting for model randomness (0.0-1.0).
            Lower values produce more deterministic results. Defaults to 0.0.
            Set to None for reasoning models (o1 series).
        pre_prompt (Optional[str]): Additional system prompt to prepend to default prompts.
        web_search (bool): Whether to enable web search capabilities. Defaults to False.
        dataverse_mcp (bool): Whether to enable Dataverse MCP integration. Defaults to False.
        prune (bool): Whether to prune the schema to only relevant fields. Defaults to False.
    """

    extraction_model: str = "gpt-4.1"
    refinement_model: Optional[str] = None
    prune_model: Optional[str] = None
    temperature: Optional[float] = 0.0
    pre_prompt: Optional[str] = None
    web_search: bool = False
    dataverse_mcp: bool = False
    prune: bool = False

    @model_validator(mode="after")
    def check_model(self):
        """Validate and set default values for model configuration.

        This validator ensures that:
        - Temperature is set to None for reasoning models (o1 series)
        - Refinement and prune models default to extraction_model if not specified

        Returns:
            The validated configuration instance.
        """
        if re.match(r"^o\d.*$", self.extraction_model):
            self.temperature = None
        if self.refinement_model is None:
            self.refinement_model = self.extraction_model
        if self.prune_model is None:
            self.prune_model = self.extraction_model
        return self


def extract_metadata(
    cls: Type[DataverseBase],
    content: Union[str, IO],
    client: OpenAI,
    config: ExtractionConfig,
    files: Optional[List[IO]] = None,
) -> DataverseBase:
    """Extract structured metadata from text content using OpenAI's language model.

    This function uses a multi-stage process to extract metadata from the provided content:
    1. Schema pruning (optional): Analyzes content to identify relevant fields
    2. Initial extraction: Generates rough JSON metadata using the LLM
    3. Refinement: Uses structured output parsing to validate and clean the metadata

    Args:
        cls (Type[DataverseBase]): The Dataverse schema class that defines the expected
            metadata structure.
        content (Union[str, IO]): The text content to analyze, either as a string or
            file-like object.
        client (OpenAI): An initialized OpenAI client instance.
        config (ExtractionConfig): Configuration object containing extraction parameters
            such as model names, temperature, and feature flags.

    Returns:
        DataverseBase: An instance of the provided schema class populated with extracted
        metadata.

    Raises:
        ValueError: If extraction fails or no output is generated.

    Example:
        >>> from openai import OpenAI
        >>> from easyDataverse.citation import CitationMetadata
        >>> from easyDataverse.llm.extraction import ExtractionConfig
        >>>
        >>> client = OpenAI(api_key="your-api-key")
        >>> config = ExtractionConfig(web_search=True, temperature=0.1)
        >>>
        >>> with open("paper.txt", "r") as f:
        ...     metadata = extract_metadata(
        ...         cls=CitationMetadata,
        ...         content=f,
        ...         client=client,
        ...         config=config
        ...     )
        >>> print(metadata.title)
    """
    if hasattr(content, "read") and not isinstance(content, str):
        input_content: str = content.read()
    else:
        input_content: str = str(content)

    if files is not None:
        file_inputs = _assemble_files(files, client)
    else:
        file_inputs = None

    text_format = _prune_schema(
        cls=cls,
        client=client,
        content=input_content,
        config=config,
        file_inputs=file_inputs,
    )

    unrefined_output = _unchecked_extract(
        text_format=text_format,
        content=input_content,
        client=client,
        config=config,
        file_inputs=file_inputs,
    )

    refined_output = _refine_output(
        text_format=text_format,
        content=unrefined_output,
        client=client,
        config=config,
    )

    return cls.model_validate_json(refined_output.model_dump_json(warnings="none"))  # type: ignore


def _unchecked_extract(
    text_format: Type[DataverseBase],
    content: str,
    client: OpenAI,
    config: ExtractionConfig,
    file_inputs: Optional[List[FileObject]] = None,
) -> str:
    """Perform initial metadata extraction to produce rough JSON output.

    This function generates an approximate JSON response based on the content and schema.
    It uses streaming responses for better performance with large structured outputs.
    The output is intentionally rough and will be refined in a subsequent step.

    Args:
        text_format (Type[DataverseBase]): The schema class defining expected structure.
        content (str): The text content to analyze.
        client (OpenAI): An initialized OpenAI client instance.
        config (ExtractionConfig): The extraction configuration.

    Returns:
        str: Raw JSON text from the model response.

    Raises:
        ValueError: If extraction fails or no output text is found.
    """
    with Status("[bold blue]Extracting metadata...", console=console) as status:
        inputs = _assemble_inputs(
            content=content,
            pre_prompt=config.pre_prompt,
            file_inputs=file_inputs,
        )

        tools = _assemble_tools(
            use_web_search=config.web_search,
            use_dv_mcp=config.dataverse_mcp,
        )

        with client.responses.create(
            input=inputs,
            model=config.extraction_model,
            temperature=config.temperature,
            tools=tools,  # type: ignore
            stream=True,
            instructions=DEFAULT_UNCHECKED_PROMPT.format(
                schema=text_format.model_json_schema()
            ),
        ) as stream:
            for event in stream:
                if event.type == "response.completed":
                    completed: ResponseCompletedEvent = event
                    console.print(
                        "[bold green]✓[/bold green] Metadata extraction completed"
                    )
                    return completed.response.output_text
                else:
                    status.update(
                        f"[bold blue]Extracting metadata...[/bold blue] ({event.type.replace('response.', '')})"
                    )

    raise ValueError("Extraction failed: No output text found")


def _refine_output(
    text_format: Type[DataverseBase],
    content: str,
    client: OpenAI,
    config: ExtractionConfig,
) -> DataverseBase:
    """Refine and validate the rough JSON output using structured parsing.

    This function takes the rough JSON output from initial extraction and uses
    OpenAI's structured output parsing to ensure it conforms to the expected schema.
    It cleans formatting issues, validates types, and ensures data integrity.

    Args:
        text_format (Type[DataverseBase]): The schema class for validation.
        content (str): The rough JSON content to refine.
        client (OpenAI): An initialized OpenAI client instance.
        config (ExtractionConfig): The extraction configuration.

    Returns:
        The parsed and validated metadata object.

    Raises:
        ValueError: If no refinement model is specified.
    """
    inputs = _assemble_inputs(
        content=content,
        pre_prompt=config.pre_prompt,
    )

    if config.refinement_model is None:
        raise ValueError("No refinement model specified")

    # Use the specialized prompt for JSON refinement
    with client.responses.stream(
        model=config.refinement_model,
        temperature=config.temperature,
        input=inputs,
        instructions=JSON_REFINEMENT_PROMPT,
        text_format=text_format,
    ) as stream:
        with Status("[bold blue]Refining metadata...", console=console) as status:
            for event in stream:
                if event.type == "response.completed":
                    status.stop()
                else:
                    status.update(
                        f"[bold blue]Refining metadata...[/bold blue] ({event.type.replace('response.', '')})"
                    )

        final_response = stream.get_final_response()
        console.print("[bold green]✓[/bold green] Refining output completed")

    return final_response.output_parsed  # type: ignore


def _prune_schema(
    cls: Type[DataverseBase],
    client: OpenAI,
    content: str,
    config: ExtractionConfig,
    file_inputs: Optional[List[FileObject]] = None,
) -> Type[DataverseBase]:
    """Prune the schema to include only fields relevant to the content.

    This function analyzes the content and schema to identify which fields are likely
    to contain extractable information. It creates a pruned version of the schema
    class that includes only relevant fields, improving extraction efficiency and accuracy.

    Args:
        cls (Type[DataverseBase]): The original schema class.
        client (OpenAI): An initialized OpenAI client instance.
        content (str): The text content to analyze.
        config (ExtractionConfig): The extraction configuration.

    Returns:
        Type[DataverseBase]: A pruned version of the schema class containing only
        relevant fields.
    """

    if config.prune:
        with Status(
            "[bold blue]Analyzing relevant fields...", console=console
        ) as status:
            fields_to_extract = _extract_relevant_fields(
                cls=cls,
                content=content,
                client=client,
                config=config,
                file_inputs=file_inputs,
            )
            status.stop()
        console.print(
            f"[bold green]✓[/bold green] Field analysis completed - {len(fields_to_extract)} relevant fields identified"
        )
    else:
        fields_to_extract = [name for name in cls.model_fields.keys()]

    with Status("[bold blue]Pruning schema...", console=console) as status:
        pruned_cls = _prune_class(cls, fields_to_extract)
        status.stop()

    console.print("[bold green]✓[/bold green] Schema pruning completed")
    return pruned_cls


def _extract_relevant_fields(
    cls: Type[DataverseBase],
    content: str,
    client: OpenAI,
    config: ExtractionConfig,
    file_inputs: Optional[List[FileObject]] = None,
) -> List[str]:
    """Identify which fields from the schema are relevant for the given content.

    This function uses an LLM to analyze the content and determine which fields
    from the schema are likely to contain extractable information. It creates
    a dynamic enum of available fields and asks the model to select relevant ones.

    Args:
        cls (Type[DataverseBase]): The schema class to analyze.
        content (str): The text content to analyze.
        client (OpenAI): An initialized OpenAI client instance.
        config (ExtractionConfig): The extraction configuration.

    Returns:
        List[str]: A list of field names that are relevant for extraction.

    Raises:
        ValueError: If no prune model is specified or no output is parsed.
    """

    fields_available = [
        {
            "name": name,
            "description": field.description,
        }
        for name, field in cls.model_fields.items()
    ]

    # Create a dynamic enum for the fields to make sure the fields are valid
    enum_name = f"{cls.__name__}Fields"
    enum_values = [field["name"] for field in fields_available]

    # Create enum dynamically using the functional API
    enum_model = Enum(enum_name, {name: name for name in enum_values})

    class PruneSchema(BaseModel):
        fields_to_extract: List[enum_model] = Field(  # type: ignore
            description="The fields that are needed to extract metadata from the provided text. Only return the fields that are needed to extract metadata from the provided text.",
        )

    content = PRUNE_TEMPLATE.format(
        fields=_fields_to_markdown_list(fields_available),
        content=content,
    )

    inputs = _assemble_inputs(
        content=content,
        pre_prompt=config.pre_prompt,
        file_inputs=file_inputs,
    )

    tools = _assemble_tools(
        use_web_search=config.web_search,
        use_dv_mcp=False,
    )

    if config.prune_model is None:
        raise ValueError("No prune model specified")

    response = client.responses.parse(
        text_format=PruneSchema,
        model=config.prune_model,
        temperature=config.temperature,
        input=inputs,
        instructions=DEFAULT_PRUNE_PROMPT,
        tools=tools,
    )

    if response.output_parsed is None:
        raise ValueError("No output parsed")

    return [field.value for field in response.output_parsed.fields_to_extract]


def _prune_class(
    cls: Type[DataverseBase],
    fields_to_extract: List[str],
):
    """Create a pruned version of the schema class with only specified fields.

    This function creates a new Pydantic model class that includes only the fields
    specified in fields_to_extract. It preserves all field metadata and excludes
    enum fields that exceed the threshold for complexity.

    Args:
        cls (Type[DataverseBase]): The original schema class.
        fields_to_extract (List[str]): List of field names to include in the pruned class.
        keep_fields (bool): Whether to keep the class. If false, will only prune enum fields.

    Returns:
        A new schema class containing only the specified fields.
    """

    fields = {}
    enum_to_exclude = _to_exclude_enums(cls)

    for name, field in cls.model_fields.items():
        if name not in fields_to_extract:
            continue
        elif name in enum_to_exclude:
            continue

        field_def = Field(
            default=field.default,
            description=field.description,
            alias=field.alias,
            title=field.title,
            validation_alias=field.validation_alias,
            json_schema_extra=field.json_schema_extra,
        )
        fields[name] = (field.annotation, field_def)

    return create_model(f"{cls.__name__}Prune", **fields, __base__=DataverseBase)


def _fields_to_markdown_list(available_fields: List[Dict[str, str]]) -> str:
    """Convert a list of field dictionaries to a markdown-formatted list.

    Args:
        available_fields (List[Dict[str, str]]): List of dictionaries containing
            field names and descriptions.

    Returns:
        str: A markdown-formatted string with field names and descriptions.
    """
    return "\n".join(
        [f"- {field['name']}: {field['description']}" for field in available_fields]
    )


def _to_exclude_enums(cls: Type[DataverseBase]) -> Set[str]:
    """Identify enum fields that should be excluded due to complexity.

    This function identifies enum fields that have too many values (exceeding
    ENUM_THRESHOLD) and should be excluded from the pruned schema to avoid
    overwhelming the LLM with too many choices.

    Args:
        cls (Type[DataverseBase]): The schema class to analyze.

    Returns:
        Set[str]: A set of field names that should be excluded.
    """

    to_exclude = set()

    for name, field in cls.model_fields.items():
        enum_class = None
        for t in get_args(field.annotation):
            if isinstance(t, type) and issubclass(t, Enum):
                enum_class = t
                break

        if enum_class is None:
            continue

        # Check if the enum has too many values
        if len(enum_class) > ENUM_THRESHOLD:
            to_exclude.add(name)

    return to_exclude


def _assemble_inputs(
    content: str,
    pre_prompt: Optional[str] = None,
    file_inputs: Optional[List[FileObject]] = None,
) -> ResponseInputParam:
    """Assemble the input messages for the OpenAI API call.

    Creates the message structure required by the OpenAI API, including the main
    content and any additional system prompts. System prompts are placed first
    in the message sequence.

    Args:
        content (str): The main text content to be processed.
        pre_prompt (Optional[str]): Optional additional system prompt to include.

    Returns:
        ResponseInputParam: A list of message dictionaries formatted for the OpenAI API.
    """

    inputs: ResponseInputParam = []

    # System prompts should come first
    if pre_prompt:
        inputs.append(
            {
                "role": "system",
                "content": pre_prompt,
            }
        )

    if file_inputs and isinstance(file_inputs, list):
        content = [  # type: ignore
            *file_inputs,
            {"type": "input_text", "text": content},
        ]

    inputs.append(
        {
            "role": "user",
            "content": content,
        }
    )

    return inputs


def _assemble_files(files: List[IO], client: OpenAI) -> List[FileObject]:
    """Assemble the files for the OpenAI API call.

    Creates the file list based on the provided files.
    """
    input_files = []
    for file in files:
        if file.name.endswith(tuple(IMAGE_EXTENSIONS)):
            purpose = "vision"
            input_type = "input_image"
        elif file.name.endswith(tuple(USER_DATA_EXTENSIONS)):
            purpose = "user_data"
            input_type = "input_file"
        else:
            raise ValueError(
                f"Unsupported file type: {file.name}. Please provide a file with one of the following extensions: {IMAGE_EXTENSIONS} or {USER_DATA_EXTENSIONS}"
            )

        file = client.files.create(file=file, purpose=purpose)
        input_files.append({"type": input_type, "file_id": file.id})

    return input_files


def _assemble_tools(
    use_web_search: bool = False,
    use_dv_mcp: bool = False,
) -> Iterable[ParseableToolParam]:
    """Assemble the tools configuration for the OpenAI API call.

    Creates the tools list based on the specified capabilities, including
    web search and Dataverse MCP integration. Tools are added conditionally
    based on the provided flags.

    Args:
        use_web_search (bool): Whether to include web search capabilities.
            Defaults to False.
        use_dv_mcp (bool): Whether to include Dataverse MCP integration.
            Defaults to False.

    Returns:
        Iterable[ParseableToolParam]: An iterable of tool parameter dictionaries
        for the OpenAI API.
    """
    tools: List[ParseableToolParam] = []

    if use_web_search:
        tools.append({"type": "web_search_preview"})

    if use_dv_mcp:
        tools.append(
            {
                "type": "mcp",
                "server_label": "dataverse_mcp",
                "server_url": DATAVERSE_MCP_URL,
                "require_approval": "never",
            }
        )

    return tools
