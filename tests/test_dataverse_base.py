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
