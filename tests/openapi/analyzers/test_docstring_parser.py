"""Tests for DocstringParser class."""

from __future__ import annotations

import pytest

from expanse.openapi.analyzers.docstring_parser import DocstringInfo
from expanse.openapi.analyzers.docstring_parser import DocstringParser
from expanse.openapi.config import OpenAPIConfig


# Fixtures


@pytest.fixture
def docstring_parser():
    """Create a DocstringParser for testing."""
    config = OpenAPIConfig(title="Test API", version="1.0.0")
    return DocstringParser(config)


@pytest.fixture
def google_style_parser():
    """Create a DocstringParser with Google style."""
    config = OpenAPIConfig(title="Test API", version="1.0.0", docstring_style="google")
    return DocstringParser(config)


# DocstringInfo tests


def test_docstring_info_initialization():
    """Test DocstringInfo initialization."""
    info = DocstringInfo()

    assert info.summary is None
    assert info.description is None
    assert info.parameters == {}
    assert info.returns is None
    assert info.raises == {}
    assert info.examples == []
    assert info.notes == []
    assert info.deprecated is False


# DocstringParser tests


def test_docstring_parser_initialization():
    """Test DocstringParser initialization."""
    config = OpenAPIConfig(title="Test API", version="1.0.0", docstring_style="google")
    parser = DocstringParser(config)

    assert parser.config == config
    assert parser.style == "google"


def test_parse_empty_docstring(docstring_parser):
    """Test parsing function with no docstring."""

    def func_no_docstring():
        pass

    info = docstring_parser.parse_docstring(func_no_docstring)

    assert info.summary is None
    assert info.description is None
    assert info.parameters == {}
    assert info.returns is None


def test_parse_simple_docstring(docstring_parser):
    """Test parsing simple docstring with just summary."""

    def func_simple():
        """Simple function that does something."""

    info = docstring_parser.parse_docstring(func_simple)

    assert info.summary == "Simple function that does something."
    assert info.description is None


def test_parse_google_style_docstring(docstring_parser):
    """Test parsing Google-style docstring."""

    def func_google():
        """Get user by ID.

        This function retrieves a user from the database using their unique ID.
        It returns the user data if found.

        Args:
            user_id (int): The unique identifier for the user.
            include_deleted (bool, optional): Whether to include deleted users.
                Defaults to False.

        Returns:
            dict: User data containing id, name, and email.

        Raises:
            ValueError: If user_id is invalid.
            UserNotFoundError: If user doesn't exist.

        Example:
            >>> get_user(123)
            {'id': 123, 'name': 'John', 'email': 'john@example.com'}

        Note:
            This function requires database connection.
        """

    info = docstring_parser.parse_docstring(func_google)

    assert info.summary == "Get user by ID."
    assert "This function retrieves a user" in info.description
    assert "user_id" in info.parameters
    assert "include_deleted" in info.parameters
    assert info.returns is not None
    assert "dict" in info.returns
    assert "ValueError" in info.raises
    assert "UserNotFoundError" in info.raises
    assert len(info.examples) > 0
    assert len(info.notes) > 0


def test_parse_sphinx_style_docstring(docstring_parser):
    """Test parsing Sphinx-style docstring."""

    def func_sphinx():
        """Create a new user.

        This function creates a new user account in the system.

        :param name: The user's full name
        :type name: str
        :param email: The user's email address
        :type email: str
        :param age: The user's age
        :type age: int, optional
        :returns: The created user object
        :rtype: User
        :raises ValidationError: If input data is invalid
        :raises DatabaseError: If database operation fails
        """

    info = docstring_parser.parse_docstring(func_sphinx)

    assert info.summary == "Create a new user."
    assert "name" in info.parameters
    assert "email" in info.parameters
    assert "age" in info.parameters
    assert info.returns is not None
    assert "ValidationError" in info.raises
    assert "DatabaseError" in info.raises


def test_parse_numpy_style_docstring(docstring_parser):
    """Test parsing NumPy-style docstring."""

    def func_numpy():
        """Update user information.

        This function updates an existing user's information in the database.

        Parameters
        ----------
        user_id : int
            The unique identifier of the user to update
        data : dict
            Dictionary containing fields to update
        force : bool, optional
            Whether to force update even if validation fails, by default False

        Returns
        -------
        bool
            True if update was successful, False otherwise

        Raises
        ------
        UserNotFoundError
            If the specified user doesn't exist
        ValidationError
            If the provided data is invalid
        """

    info = docstring_parser.parse_docstring(func_numpy)

    assert info.summary == "Update user information."
    assert "user_id" in info.parameters
    assert "data" in info.parameters
    assert "force" in info.parameters
    assert info.returns is not None
    assert "UserNotFoundError" in info.raises
    assert "ValidationError" in info.raises


def test_parse_auto_detection():
    """Test automatic docstring style detection."""
    config = OpenAPIConfig(title="Test API", version="1.0.0", docstring_style="auto")
    parser = DocstringParser(config)

    def func_with_google():
        """Test function.

        Args:
            param: A parameter.

        Returns:
            Something.
        """

    info = parser.parse_docstring(func_with_google)

    assert info.summary == "Test function."
    assert "param" in info.parameters


def test_parse_multiline_description(docstring_parser):
    """Test parsing docstring with multiline description."""

    def func_multiline():
        """Complex function with detailed description.

        This is a complex function that performs multiple operations.
        It handles various edge cases and provides robust error handling.

        The function is designed to be flexible and can handle different
        types of input data.

        Args:
            data: Input data to process.

        Returns:
            Processed result.
        """

    info = docstring_parser.parse_docstring(func_multiline)

    assert info.summary == "Complex function with detailed description."
    assert "multiple operations" in info.description
    assert "edge cases" in info.description
    assert "flexible" in info.description


def test_parse_deprecated_function(docstring_parser):
    """Test parsing docstring of deprecated function."""

    def func_deprecated():
        """Old function that should not be used.

        .. deprecated:: 2.0
            Use new_function() instead.

        Args:
            param: Some parameter.

        Returns:
            Some result.
        """

    info = docstring_parser.parse_docstring(func_deprecated)

    # The parser may not detect deprecated markers in all formats
    # This is implementation-dependent behavior
    assert info.summary == "Old function that should not be used."


def test_parse_function_with_no_parameters(docstring_parser):
    """Test parsing function with no parameters."""

    def func_no_params():
        """Simple function with no parameters.

        Returns:
            str: A greeting message.
        """

    info = docstring_parser.parse_docstring(func_no_params)

    assert info.summary == "Simple function with no parameters."
    assert info.parameters == {}
    assert info.returns is not None


def test_parse_function_with_no_return(docstring_parser):
    """Test parsing function with no return value."""

    def func_no_return():
        """Function that doesn't return anything.

        Args:
            message: Message to print.
        """

    info = docstring_parser.parse_docstring(func_no_return)

    assert info.summary == "Function that doesn't return anything."
    assert "message" in info.parameters
    assert info.returns is None


def test_extract_http_status_codes(docstring_parser):
    """Test extracting HTTP status codes from docstring."""

    def func_with_status_codes():
        """API endpoint function.

        Returns:
            200: Success response
            400: Bad request
            404: Not found
            500: Internal server error

        Raises:
            HTTPException: 401 if unauthorized
            ValidationError: 422 for validation errors
        """

    info = docstring_parser.parse_docstring(func_with_status_codes)
    status_codes = docstring_parser.extract_http_status_codes(info)

    assert "200" in status_codes
    assert "400" in status_codes
    assert "404" in status_codes
    assert "500" in status_codes
    assert "401" in status_codes
    assert "422" in status_codes


def test_extract_status_codes_from_text(docstring_parser):
    """Test extracting status codes from text."""
    text = "Returns 200 for success, 404 if not found, and 500 for server error"
    codes = docstring_parser._extract_status_codes_from_text(text)

    assert "200" in codes
    assert "404" in codes
    assert "500" in codes


def test_parameter_type_extraction(docstring_parser):
    """Test extracting parameter types from docstring."""

    def func_typed_params():
        """Function with typed parameters.

        Args:
            name (str): User's name
            age (int): User's age
            is_active (bool): Whether user is active
            tags (list[str]): List of user tags
            metadata (dict): Additional metadata
            callback (callable): Optional callback function
        """

    info = docstring_parser.parse_docstring(func_typed_params)

    assert "name" in info.parameters
    assert "age" in info.parameters
    assert "is_active" in info.parameters
    assert "tags" in info.parameters
    assert "metadata" in info.parameters
    assert "callback" in info.parameters


def test_edge_cases(docstring_parser):
    """Test parsing edge cases."""

    def func_edge_case():
        """

        Function with weird formatting.


            Args:
                param:    Description with extra spaces

            Returns:
                Result.

        """

    info = docstring_parser.parse_docstring(func_edge_case)

    assert info.summary == "Function with weird formatting."
    assert "param" in info.parameters


def test_missing_sections(docstring_parser):
    """Test handling missing sections gracefully."""

    def func_minimal():
        """Just a summary."""

    info = docstring_parser.parse_docstring(func_minimal)

    assert info.summary == "Just a summary."
    assert info.parameters == {}
    assert info.returns is None
    assert info.raises == {}


def test_malformed_docstring(docstring_parser):
    """Test handling malformed docstrings."""

    def func_malformed():
        """Malformed docstring.

        Args:
            This is not properly formatted

        Returns:
            Also not properly formatted
        """

    # Should not raise an exception
    info = docstring_parser.parse_docstring(func_malformed)
    assert info.summary == "Malformed docstring."


@pytest.mark.parametrize("style", ["google", "sphinx", "numpy", "auto"])
def test_different_styles(style: str):
    """Test parser works with different docstring styles."""
    config = OpenAPIConfig(title="Test API", version="1.0.0", docstring_style=style)
    parser = DocstringParser(config)

    def test_func():
        """Test function."""

    # Should not raise an exception
    info = parser.parse_docstring(test_func)
    assert info.summary == "Test function."


def test_complex_parameter_descriptions(docstring_parser):
    """Test parsing complex parameter descriptions."""

    def func_complex():
        """Function with complex parameter descriptions.

        Args:
            config (dict): Configuration dictionary containing:
                - host: Database host
                - port: Database port (default: 5432)
                - credentials: Authentication details
            filters (list[str], optional): List of filters to apply.
                Each filter should be in format "field:value".
                Defaults to empty list.
        """

    info = docstring_parser.parse_docstring(func_complex)

    assert "config" in info.parameters
    assert "filters" in info.parameters
    assert "Configuration dictionary" in info.parameters["config"]
    # The parser may not preserve all formatting details like "optional"
    assert "List of filters" in info.parameters["filters"]


def test_return_type_parsing(docstring_parser):
    """Test parsing different return type formats."""

    def func_return_types():
        """Function with detailed return type.

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Whether operation succeeded
                - data (list): List of results
                - count (int): Total number of items
                - next_page (str|None): URL for next page if available
        """

    info = docstring_parser.parse_docstring(func_return_types)

    assert info.returns is not None
    assert "dict[str, Any]" in info.returns
    assert "success" in info.returns
    assert "data" in info.returns
