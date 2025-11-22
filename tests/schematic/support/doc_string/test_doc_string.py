from expanse.schematic.support.doc_string.doc_string import DocString


def test_docstring_parser_parses_google_style():
    def handler(user_id: int, name: str) -> dict:
        """
        Get a user by ID.

        This is a longer description of what the function does.

        Args:
            user_id (int): The user ID to fetch
            name: The name to filter by

        Returns:
            A dictionary containing user information

        Raises:
            HTTPException: (404) User not found
            ValueError: Invalid user ID format
        """
        return {}

    info = DocString.parse(handler.__doc__ or "")

    assert info.summary == "Get a user by ID."
    assert (
        info.description.strip()
        == "This is a longer description of what the function does."
    )

    assert "user_id" in info.parameters
    assert info.parameters["user_id"].description == "The user ID to fetch"
    assert info.parameters["user_id"].type_hint == "int"

    assert "name" in info.parameters
    assert info.parameters["name"].description == "The name to filter by"

    assert info.returns == "A dictionary containing user information"

    assert len(info.raises) == 2
    assert info.raises[0].exception == "HTTPException"
    assert info.raises[0].status_code == 404
    assert info.raises[0].description == "User not found"


def test_docstring_parser_parses_sphinx_style():
    def handler(user_id: int) -> dict:
        """
        Get a user by ID.

        This is a longer description of what the function does.

        :param user_id: The user ID to fetch
        :type user_id: int

        :returns: A dictionary containing user information
        :rtype: dict

        :raises HTTPException: (404) User not found
        """
        return {}

    info = DocString.parse(handler.__doc__ or "")

    assert info.summary == "Get a user by ID."
    assert (
        info.description.strip()
        == "This is a longer description of what the function does."
    )

    assert "user_id" in info.parameters
    assert info.parameters["user_id"].description == "The user ID to fetch"
    assert info.parameters["user_id"].type_hint == "int"

    assert info.returns == "A dictionary containing user information"
    assert info.return_type == "dict"

    assert len(info.raises) == 1
    assert info.raises[0].exception == "HTTPException"
    assert info.raises[0].status_code == 404


def test_docstring_parser_parses_plain_text():
    def handler() -> dict:
        """
        This is a simple docstring.

        It has multiple lines.
        """
        return {}

    info = DocString.parse(handler.__doc__ or "")

    assert info.summary == "This is a simple docstring."
    assert "multiple lines" in info.description
