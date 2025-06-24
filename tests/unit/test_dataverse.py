import pytest

from easyDataverse.dataverse import Dataverse


class TestDataverse:
    @pytest.mark.unit
    def test_invalid_url(self):
        """Test that an invalid URL raises a ValueError"""
        with pytest.raises(ValueError):
            Dataverse(
                server_url="not a url",  # type: ignore
                api_token="9eb39a88-ab0d-415d-80c2-32cbafdb5f6f",  # type: ignore
            )

    @pytest.mark.unit
    def test_invalid_api_token(self):
        """Test that an invalid API token raises a ValueError"""
        with pytest.raises(ValueError):
            Dataverse(
                server_url="http://localhost:8080",  # type: ignore
                api_token="not a uuid",  # type: ignore
            )

    @pytest.mark.unit
    def test_valid_versions(self):
        """Test that the version is compliant"""
        cases = [
            "6.0",
            "6.1",
            "5.13",
            "5.14",
            "v6.0",
            "v5.14",
            "v5.13-beta",
            "6.1.0",
        ]

        for version in cases:
            major, minor = Dataverse._extract_major_minor(version)
            assert Dataverse._check_version(major, minor)

    @pytest.mark.unit
    def test_invalid_version(self):
        """Test that an invalid version raises a ValueError"""
        with pytest.raises(ValueError):
            Dataverse._extract_major_minor("not a version")

    @pytest.mark.unit
    def test_unsupported_version(self):
        """Test that the version is compliant"""
        cases = [
            "4.0",
            "4.1",
            "5.12",
            "5.11",
        ]
        for version in cases:
            major, minor = Dataverse._extract_major_minor(version)
            assert not Dataverse._check_version(major, minor)
