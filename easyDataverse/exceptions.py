class ControlledVocabularyError(Exception):
    """Raises an error if a value provided by a controlled vocabulary doesnt match"""
    pass


class MissingCredentialsException(Exception):
    """Throws an exception if credentials are not provided in the environment variables"""

    def __init__(self) -> None:
        self.message = (
            "Please specify your API Token in your environment variables with the key 'DATAVERSE_API_TOKEN'"
        )

        super().__init__(self.message)


class MissingURLException(Exception):
    """Throws an exception if no dataverse URL has been provided in the environment variables"""

    def __init__(self) -> None:
        self.message = (
            "Please specify a Dataverse instance URL in your environment variables with the key 'DATAVERSE_URL'"
        )

        super().__init__(self.message)


class DatasetAlreadyExistsException(Exception):
    """Throws an exception if the dataset has already been uploaded --> Existing p_id in Dataset"""

    def __init__(self, p_id) -> None:
        self.message = (
            f"The dataset has already been uploaded to your Dataverse, since the Dataset object has a given 'p_id' of {p_id}. \
            This error might be the cause of double execution of the Dataset's upload method. However, if you want to update your \
            dataset, use the Dataset's update method."
        )

        super().__init__(self.message)


class ValidationError(Exception):
    """Throws an exception if validation failed and prints the error message"""
    pass
