import importlib
import sys
import json

from easyDataverse.tools.codegen.generator import generate_python_api


class TestDataverseBase:
    def test_from_json_string(self, dataverse_base_class):
        """Tests whether the init from a JSON string works"""

        # Get class to test
        test_class = dataverse_base_class

        # Set up JSON input
        json_in = '{"foo":"foo", "bar":"bar"}'

        # Set up expected output
        expected = test_class(foo="foo", bar="bar")

        assert (
            test_class.from_json_string(json_in) == expected
        ), "JSON string init does not work properly"

    def test_from_json_file(self, dataverse_base_class):
        """Tests whether the init from a JSON file works"""

        # Get class to test
        test_class = dataverse_base_class

        # Set up JSON input
        json_in = "./tests/fixtures/dataversebase/json_input.json"

        # Set up expected output
        expected = test_class(foo="foo", bar="bar")

        assert (
            test_class.from_json_file(json_in) == expected
        ), "JSON file init does not work properly"

    def test_from_yaml_string(self, dataverse_base_class):
        """Tests whether the init from a YAML string works"""

        # Get class to test
        test_class = dataverse_base_class

        # Set up JSON input
        yaml_in = "foo: foo\nbar: bar"

        # Set up expected output
        expected = test_class(foo="foo", bar="bar")

        assert (
            test_class.from_yaml_string(yaml_in) == expected
        ), "YAML string init does not work properly"

    def test_from_yaml_file(self, dataverse_base_class):
        """Tests whether the init from a YAML file works"""

        # Get class to test
        test_class = dataverse_base_class

        # Set up JSON input
        yaml_in = "./tests/fixtures/dataversebase/yaml_input.yaml"

        # Set up expected output
        expected = test_class(foo="foo", bar="bar")

        assert (
            test_class.from_yaml_file(yaml_in) == expected
        ), "YAML file init does not work properly"

    def test_json_schema_export(self, metadatablock_json_schema):
        """Tests whether the given metadatablock schema export is correct"""

        def _get_module(name: str, loc: str):
            """Fetches a module from a loc"""

            spec = importlib.util.spec_from_file_location(name, loc)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)

            return module

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

        assert json.loads(block.ToyDataset.json_schema()) == json.loads(
            metadatablock_json_schema
        ), f"Metadatablock JSON schema is wrong."
