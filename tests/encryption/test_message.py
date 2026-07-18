import pytest

from expanse.encryption.errors import MessageDecodeError
from expanse.encryption.message import Message


def test_message_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value", "foo": 42})
    dumped = message.dump()

    assert dumped == '{"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}'


def test_message_with_bytes_header_value_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value", "bytes": b"bytes"})
    dumped = message.dump()

    assert (
        dumped == '{"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "bytes": "Ynl0ZXM="}}'
    )


def test_message_can_be_encoded_to_base64() -> None:
    message = Message(b"payload", {"key": "value", "foo": 42})
    dumped = message.encode()

    assert (
        dumped
        == "eyJwIjogImNHRjViRzloWkE9PSIsICJoIjogeyJrZXkiOiAiZG1Gc2RXVT0iLCAiZm9vIjogNDJ9fQ=="
    )


def test_message_is_representable() -> None:
    message = Message(b"payload", {"key": "value"})

    assert repr(message) == "Message(b'payload', {'key': 'value'})"


def test_message_can_be_loaded_from_json_encoded_data() -> None:
    dumped = '{"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}'
    message = Message.load(dumped)

    assert message.payload == b"payload"
    assert message.headers == {"key": b"value", "foo": 42}


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        "[1, 2, 3]",
        '"a string"',
        '{"h": {}}',
        '{"p": "cGF5bG9hZA=="}',
        '{"p": 42, "h": {}}',
        '{"p": "cGF5bG9hZA==", "h": []}',
        '{"p": "invalid base64", "h": {}}',
        '{"p": "cGF5bG9hZA==", "h": {"iv": "invalid base64"}}',
    ],
)
def test_message_load_rejects_malformed_data(value: str) -> None:
    with pytest.raises(MessageDecodeError):
        Message.load(value)


def test_message_can_be_decoded_from_base64_encoded_data() -> None:
    dumped = "eyJwIjogImNHRjViRzloWkE9PSIsICJoIjogeyJrZXkiOiAiZG1Gc2RXVT0iLCAiZm9vIjogNDJ9fQ=="
    message = Message.decode(dumped)

    assert message.payload == b"payload"
    assert message.headers == {"key": b"value", "foo": 42}
