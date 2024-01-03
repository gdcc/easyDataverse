class MissingCredentialsException(Exception):
    """Throws an exception if credentials are not provided in the environment variables"""

    def __init__(self) -> None:
        self.message = "Please specify your API Token in your environment variables with the key 'DATAVERSE_API_TOKEN'"

        super().__init__(self.message)


class MissingURLException(Exception):
    """Throws an exception if no dataverse URL has been provided in the environment variables"""

    def __init__(self) -> None:
        self.message = "Please specify a Dataverse instance URL in your environment variables with the key 'DATAVERSE_URL'"

        super().__init__(self.message)
