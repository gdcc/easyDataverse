from enum import Enum
from typing import List, Optional, Union, get_args

import pytest
from pydantic import BaseModel, Field

from easyDataverse.classgen import (
    camel_to_snake,
    clean_name,
    construct_class_name,
    create_function_signature,
    find_common_name_part,
    generate_add_function,
    get_field_type,
    list_type,
    optional_type,
    prepare_field_meta,
    process_name,
    remove_child_fields_from_global,
    spaced_to_snake,
    union_type,
)


class TestFindCommonNamePart:
    # The function correctly identifies a common prefix among a list of names.
    @pytest.mark.unit
    def test_common_prefix(self):
        names = ["abc_def", "abc_ghi", "abc_jkl"]
        result = find_common_name_part(names)
        assert result == "abc_"

    # The function returns an empty string when given an empty list of names.
    @pytest.mark.unit
    def test_empty_list(self):
        names = []
        result = find_common_name_part(names)
        assert result == ""

    # The function correctly identifies a common suffix among a list of names.
    @pytest.mark.unit
    def test_common_suffix(self):
        names = ["def_abc", "ghi_abc", "jkl_abc"]
        result = find_common_name_part(names)
        assert result == ""

    # The function returns an empty string when given a list with only one name.
    @pytest.mark.unit
    def test_single_name(self):
        names = ["abc"]
        result = find_common_name_part(names)
        assert result == ""

    # The function correctly identifies a common prefix when given a list of names with only one character each.
    @pytest.mark.unit
    def test_single_char_prefix(self):
        names = ["a", "a", "a"]
        result = find_common_name_part(names)
        assert result == "a_"

    # The function correctly identifies a common suffix when given a list of names with only one character each.
    @pytest.mark.unit
    def test_single_char_suffix(self):
        names = ["a", "b", "c"]
        result = find_common_name_part(names)
        assert result == ""


class TestProcessName:
    # Converts camel case to snake case.
    @pytest.mark.unit
    def test_convert_camel_case_to_snake_case(self):
        # Arrange
        attr_name = "camelCaseAttribute"
        common_part = ""

        # Act
        processed_name = process_name(attr_name, common_part)

        # Assert
        assert processed_name == "camel_case_attribute"

    # Returns processed attribute name.
    @pytest.mark.unit
    def test_returns_processed_attribute_name(self):
        # Arrange
        attr_name = "camelCaseAttribute"
        common_part = ""

        # Act
        processed_name = process_name(attr_name, common_part)

        # Assert
        assert processed_name == "camel_case_attribute"

    # Empty attribute name returns empty string.
    @pytest.mark.unit
    def test_empty_attribute_name_returns_empty_string(self):
        # Arrange
        attr_name = ""
        common_part = ""

        # Act
        processed_name = process_name(attr_name, common_part)

        # Assert
        assert processed_name == ""

    # Empty common part returns processed attribute name without common part.
    @pytest.mark.unit
    def test_empty_common_part_returns_processed_attribute_name_without_common_part(
        self,
    ):
        # Arrange
        attr_name = "commonPartAttribute"
        common_part = ""

        # Act
        processed_name = process_name(attr_name, common_part)

        # Assert
        assert processed_name == "common_part_attribute"

    # Attribute name with no camel case returns attribute name in snake case.
    @pytest.mark.unit
    def test_attribute_name_with_no_camel_case_returns_attribute_name_in_snake_case(
        self,
    ):
        # Arrange
        attr_name = "attribute_name"
        common_part = ""

        # Act
        processed_name = process_name(attr_name, common_part)

        # Assert
        assert processed_name == "attribute_name"


class TestRemoveChildFieldsFromGlobal:
    # Removes all child fields from a dictionary with compound fields.
    @pytest.mark.unit
    def test_remove_child_fields_from_compound(self):
        # Arrange
        fields = {
            "field1": {
                "childFields": {
                    "child1": {},
                    "child2": {},
                },
            },
            "child1": {},
        }

        expected_result = {
            "field1": {
                "childFields": {
                    "child1": {},
                    "child2": {},
                },
            },
        }

        # Act
        result = remove_child_fields_from_global(fields)

        # Assert
        assert result == expected_result

    # Handles a dictionary with no child fields and returns it unchanged.
    @pytest.mark.unit
    def test_no_child_fields(self):
        # Arrange
        fields = {"field1": {}, "field2": {}, "field3": {}}

        expected_result = {"field1": {}, "field2": {}, "field3": {}}

        # Act
        result = remove_child_fields_from_global(fields)

        # Assert
        assert result == expected_result


class TestUnionType:
    # Returns a Union typing encapsulating the given types
    @pytest.mark.unit
    def test_returns_union_typing(self):
        # Arrange
        dtypes = (int, str, bool)

        # Act
        result = union_type(dtypes)

        # Assert
        assert result == Union[int, str, bool]

    # Works correctly with multiple types in the input tuple
    @pytest.mark.unit
    def test_works_with_multiple_types(self):
        # Arrange
        dtypes = (int, str, bool)

        # Act
        result = union_type(dtypes)

        # Assert
        assert result == Union[int, str, bool]

    # Raises a ValueError if only a single type is provided
    @pytest.mark.unit
    def test_raises_value_error_with_single_type(self):
        # Arrange
        dtypes = (int,)

        # Act and Assert
        with pytest.raises(ValueError):
            union_type(dtypes)

    # Handles empty input tuples correctly
    @pytest.mark.unit
    def test_handles_empty_input_tuple(self):
        # Arrange
        dtypes = ()

        # Act and Assert
        with pytest.raises(ValueError):
            union_type(dtypes)

    # Raises a TypeError if the input argument is not a tuple
    @pytest.mark.unit
    def test_raises_type_error_with_non_tuple_input(self):
        # Arrange
        dtypes = [int, str, bool]

        # Act and Assert
        with pytest.raises(TypeError):
            union_type(dtypes)

    # Raises a TypeError if the input tuple contains non-type elements
    @pytest.mark.unit
    def test_raises_type_error_with_non_type_elements(self):
        # Arrange
        dtypes = (int, str, 10)

        # Act and Assert
        with pytest.raises(TypeError):
            union_type(dtypes)


class TestConstructClassName:
    # Converts a display name with spaces to a class name with capitalized words.
    @pytest.mark.unit
    def test_convert_display_name_with_spaces(self):
        # Arrange
        display_name = "hello world"

        # Act
        result = construct_class_name(display_name)

        # Assert
        assert result == "HelloWorld"

    # Converts a display name with hyphens to a class name with capitalized words.
    @pytest.mark.unit
    def test_convert_display_name_with_hyphens(self):
        # Arrange
        display_name = "hello-world"

        # Act
        result = construct_class_name(display_name)

        # Assert
        assert result == "HelloWorld"

    # Converts a display name with mixed cases to a class name with capitalized words.
    @pytest.mark.unit
    def test_convert_display_name_with_mixed_cases(self):
        # Arrange
        display_name = "HeLlO wOrLd"

        # Act
        result = construct_class_name(display_name)

        # Assert
        assert result == "HelloWorld"

    # Converts an empty string to a class name and expects a ValueError to be raised.
    @pytest.mark.unit
    def test_convert_empty_string(self):
        # Arrange
        display_name = ""

        # Act and Assert
        with pytest.raises(ValueError):
            construct_class_name(display_name)


class TestSpacedToSnake:
    # Converts a name with spaces to snake case.
    @pytest.mark.unit
    def test_convert_name_with_spaces(self):
        name = "hello world"
        expected = "hello_world"
        assert spaced_to_snake(name) == expected

    # Raises a ValueError if the input name is empty after cleaning.
    @pytest.mark.unit
    def test_raise_value_error_for_empty_name(self):
        name = ""
        with pytest.raises(ValueError):
            spaced_to_snake(name)

    # Returns the snake case version of the input name even if it contains non-alphanumeric characters.
    @pytest.mark.unit
    def test_convert_name_with_non_alphanumeric_characters(self):
        name = "hello!@#$%^&*()_+"
        expected = "hello"
        assert spaced_to_snake(name) == expected

    # Returns the snake case version of the input name.
    @pytest.mark.unit
    def test_convert_name_to_snake_case(self):
        name = "Hello World"
        expected = "hello_world"
        assert spaced_to_snake(name) == expected


class TestCamelToSnake:
    # Converts a simple camel case string to snake case.
    @pytest.mark.unit
    def test_simple_camel_case(self):
        # Arrange
        name = "simpleCamelCase"

        # Act
        result = camel_to_snake(name)

        # Assert
        assert result == "simple_camel_case"

    # Converts a camel case string with multiple capital letters to snake case.
    @pytest.mark.unit
    def test_multiple_capital_letters(self):
        # Arrange
        name = "camelCaseWithMultipleCapitalLetters"

        # Act
        result = camel_to_snake(name)

        # Assert
        assert result == "camel_case_with_multiple_capital_letters"

    # Converts a camel case string with numbers to snake case.
    @pytest.mark.unit
    def test_numbers_in_camel_case(self):
        # Arrange
        name = "camelCaseWithNumbers123"

        # Act
        result = camel_to_snake(name)

        # Assert
        assert result == "camel_case_with_numbers123"

    # Converts an empty string to an empty string.
    @pytest.mark.unit
    def test_empty_string(self):
        # Arrange
        name = ""

        # Act
        result = camel_to_snake(name)

        # Assert
        assert result == ""


class TestCleanName:
    # The function should return the input string if it contains only valid variable name characters.
    @pytest.mark.unit
    def test_valid_variable_name(self):
        assert clean_name("valid_variable_name") == "valid_variable_name"
        assert clean_name("123") == "123"
        assert clean_name("_underscore") == "_underscore"
        assert clean_name("camelCase") == "camelCase"
        assert clean_name("snake_case") == "snake_case"
        assert clean_name("mixed123Case") == "mixed123Case"

    # The function should remove any non-alphanumeric characters from the input string.
    @pytest.mark.unit
    def test_remove_non_alphanumeric(self):
        assert clean_name("name123!") == "name123"
        assert clean_name("name@#$%^&*()") == "name"
        assert clean_name("name_123") == "name_123"
        assert clean_name("name-123") == "name 123"
        assert clean_name("name 123") == "name 123"
        assert clean_name("name!") == "name"

    # The function should replace spaces with underscores in the input string.
    @pytest.mark.unit
    def test_replace_spaces_with_underscores(self):
        assert clean_name("name with spaces") == "name with spaces"
        assert clean_name("name_with_spaces") == "name_with_spaces"
        assert clean_name("name-with-spaces") == "name with spaces"
        assert clean_name("name_123") == "name_123"
        assert clean_name("name!") == "name"

    # The function should return an empty string if the input string contains only non-alphanumeric characters.
    @pytest.mark.unit
    def test_empty_string(self):
        assert clean_name("!@#$%^&*()") == ""
        assert clean_name(" ") == ""
        assert clean_name("-") == ""
        assert clean_name("_") == "_"
        assert clean_name("") == ""

    # The function should remove leading and trailing whitespace from the input string.
    @pytest.mark.unit
    def test_remove_whitespace(self):
        assert clean_name("  name  ") == "name"
        assert clean_name("name") == "name"
        assert clean_name("  name") == "name"
        assert clean_name("name  ") == "name"
        assert clean_name("  ") == ""


class TestCreateFunctionSignature:
    # The function should return a list of inspect.Parameter objects that
    # correctly represent the input model.
    @pytest.mark.unit
    def test_create_function_signature(self):
        # Arrange
        class TestClass(BaseModel):
            """Test class for pydantic."""

            name: str
            value: int = 42
            optional: Optional[str] = None

        # Act
        result = create_function_signature(TestClass)

        # Assert
        assert result[0].name == "name"
        assert result[0].default.__name__ == "empty"
        assert result[0].type == str
        assert result[1].name == "value"
        assert result[1].type == int
        assert result[1].default.__name__ == "empty"
        assert result[2].name == "optional"
        assert result[2].type == Optional[str]
        assert result[2].default == None


class TestGenerateAddFuntion:
    @pytest.mark.unit
    def test_generate_add_function(self):
        # Arrange
        class TestClass(BaseModel):
            """Test class for pydantic."""

            name: str
            value: int = 42
            optional: Optional[str] = None

        class ParentClass(BaseModel):
            to_add_to: List[TestClass] = []

        # Act
        result = generate_add_function(
            TestClass,
            "to_add_to",
            "fun_name",
        )

        setattr(
            ParentClass,
            "fun_name",
            result,
        )

        instance = ParentClass()
        instance.fun_name(
            name="name",
            value=42,
            optional=None,
        )

        # Assert
        expected_annotation = {
            "name": str,
            "value": int,
            "optional": Optional[str],
        }

        expected_object = TestClass(
            name="name",
            value=42,
            optional=None,
        )

        assert result.__name__ == "fun_name"
        assert result.__annotations__ == expected_annotation
        assert isinstance(instance.to_add_to[0], TestClass)
        assert instance.to_add_to[0].model_dump() == expected_object.model_dump()


class TestOptionalType:
    @pytest.mark.unit
    def test_optional_type(self):
        # Arrange
        dtype = int

        # Act
        result = optional_type(dtype)

        # Assert
        assert result == Optional[int]


class TestListType:
    @pytest.mark.unit
    def test_list_type(self):
        # Arrange
        dtype = int

        # Act
        result = list_type(dtype)

        # Assert
        assert result == List[int]


class TestPrepareFieldMeta:
    @pytest.mark.unit
    def test_single_primitive_field(self):
        # Arrange
        field = {
            "name": "single_text_field",
            "multiple": False,
            "type": "TEXT",
            "isControlledVocabulary": False,
            "description": "A single text field",
        }

        # Act
        result = prepare_field_meta(field)

        # Assert
        expected = Field(
            multiple=False,
            typeClass="primitive",
            typeName="single_text_field",
            description="A single text field",
            default=None,
        )

        assert result.json_schema_extra == expected.json_schema_extra
        assert result.default == expected.default
        assert result.annotation == expected.annotation
        assert result.is_required() == False

    @pytest.mark.unit
    def test_multiple_primitive_field(self):
        # Arrange
        field = {
            "name": "multiple_text_field",
            "multiple": True,
            "type": "TEXT",
            "isControlledVocabulary": False,
            "description": "A multiple text field",
        }

        # Act
        result = prepare_field_meta(field)

        # Assert
        expected = Field(
            multiple=True,
            typeClass="primitive",
            typeName="multiple_text_field",
            description="A multiple text field",
            default_factory=list,
        )

        assert result.json_schema_extra == expected.json_schema_extra
        assert result.default_factory == expected.default_factory
        assert result.annotation == expected.annotation
        assert result.is_required() == False

    @pytest.mark.unit
    def test_compound_field(self):
        # Arrange
        field = {
            "name": "single_compound_field",
            "multiple": False,
            "type": "NONE",
            "isControlledVocabulary": False,
            "description": "A single compound field",
        }

        # Act
        result = prepare_field_meta(field)

        # Assert
        expected = Field(
            multiple=False,
            typeClass="compound",
            typeName="single_compound_field",
            description="A single compound field",
            default=None,
        )

        assert result.json_schema_extra == expected.json_schema_extra
        assert result.default_factory == expected.default_factory
        assert result.annotation == expected.annotation
        assert result.is_required() == False

    @pytest.mark.unit
    def test_controlled_vocab_field(self):
        # Arrange
        field = {
            "name": "single_cv_field",
            "multiple": False,
            "type": "TEXT",
            "isControlledVocabulary": True,
            "description": "A single CV field",
        }

        # Act
        result = prepare_field_meta(field)

        # Assert
        expected = Field(
            multiple=False,
            typeClass="controlledVocabulary",
            typeName="single_cv_field",
            description="A single CV field",
            default=None,
        )

        assert result.json_schema_extra == expected.json_schema_extra
        assert result.default_factory == expected.default_factory
        assert result.annotation == expected.annotation
        assert result.is_required() == False


class TestGetFieldType:
    @pytest.mark.unit
    def test_single_cv_field(self):
        # Arrange
        field = {
            "name": "single_cv_field",
            "multiple": False,
            "type": "TEXT",
            "isControlledVocabulary": True,
            "description": "A single CV field",
            "controlledVocabularyValues": [
                "value1",
                "value2",
            ],
        }

        # Act
        result = get_field_type(field)

        # Assert
        generated_enum = get_args(result)[0]
        assert get_args(result)[1] == type(None)
        assert issubclass(generated_enum, Enum)
        assert generated_enum.__name__ == "single_cv_field"
        assert generated_enum.VALUE1.value == "value1"
        assert generated_enum.VALUE2.value == "value2"

    @pytest.mark.unit
    def test_single_primitive_field(self):
        # Arrange
        field = {
            "name": "single_primitive_field",
            "multiple": False,
            "type": "TEXT",
            "isControlledVocabulary": False,
            "description": "A single primitive field",
        }

        # Act
        result = get_field_type(field)

        # Assert
        assert result == Optional[str]

    @pytest.mark.unit
    def test_multiple_primitive_field(self):
        # Arrange
        field = {
            "name": "single_primitive_field",
            "multiple": True,
            "type": "TEXT",
            "isControlledVocabulary": False,
            "description": "A single primitive field",
        }

        # Act
        result = get_field_type(field)

        # Assert
        assert result == List[str]
