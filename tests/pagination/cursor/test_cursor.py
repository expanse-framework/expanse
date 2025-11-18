import pytest

from expanse.pagination.cursor.cursor import Cursor
from expanse.pagination.cursor.exceptions import InvalidCursorParameter


def test_cursor_can_be_encoded() -> None:
    cursor = Cursor({"id": 123, "name": "Alice"})

    encoded = cursor.encode()
    assert isinstance(encoded, str)
    assert len(encoded) > 0


def test_cursor_can_be_decoded() -> None:
    original_cursor = Cursor({"id": 123, "name": "Alice"})
    encoded = original_cursor.encode()

    decoded_cursor = Cursor.decode(encoded)
    assert decoded_cursor == original_cursor

    assert original_cursor == decoded_cursor


def test_cursor_decode_invalid_data() -> None:
    assert Cursor.decode("invalid_base64_string") is None
    assert Cursor.decode("aW52YWxpZF9qc29u") is None  # base64 for "invalid_json"


def test_cursor_reversion() -> None:
    cursor = Cursor({"id": 123, "name": "Alice"})
    assert not cursor.is_reversed()

    reverted_cursor = cursor.revert()

    assert cursor != reverted_cursor
    assert cursor.parameters == reverted_cursor.parameters
    assert reverted_cursor.is_reversed()


def test_cursor_equality() -> None:
    cursor1 = Cursor({"id": 123, "name": "Alice"})
    cursor2 = Cursor({"id": 123, "name": "Alice"})
    cursor3 = Cursor({"id": 456, "name": "Bob"})

    assert cursor1 == cursor2
    assert cursor1 != cursor3

    assert cursor1 != "foo"


def test_missing_parameter_access() -> None:
    cursor = Cursor({"id": 123})

    assert cursor.parameter("id") == 123

    with pytest.raises(InvalidCursorParameter):
        assert cursor.parameter("name") is None
