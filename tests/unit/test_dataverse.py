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
