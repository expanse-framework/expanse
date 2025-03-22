from expanse.encryption.message import Message


def test_message_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value", "foo": 42})
    dumped = message.dump()

    assert dumped == {"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}


def test_message_with_bytes_header_value_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value", "bytes": b"bytes"})
    dumped = message.dump()

    assert dumped == {
        "p": "cGF5bG9hZA==",
        "h": {"key": "dmFsdWU=", "bytes": "Ynl0ZXM="},
    }


def test_message_is_dumpable_to_base64() -> None:
    message = Message(b"payload", {"key": "value", "foo": 42})
    dumped = message.dump("base64")

    assert (
        dumped
        == "eyJwIjogImNHRjViRzloWkE9PSIsICJoIjogeyJrZXkiOiAiZG1Gc2RXVT0iLCAiZm9vIjogNDJ9fQ=="
    )


def test_message_is_dumpable_to_json() -> None:
    message = Message(b"payload", {"key": "value", "foo": 42})
    dumped = message.dump("json")

    assert dumped == '{"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}'


def test_message_is_representable() -> None:
    message = Message(b"payload", {"key": "value"})

    assert repr(message) == "Message(b'payload', {'key': 'value'})"


def test_message_can_be_loaded_from_dumped_data() -> None:
    dumped = {"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}
    message = Message.load(dumped)

    assert message.payload == b"payload"
    assert message.headers == {"key": b"value", "foo": 42}


def test_message_can_be_loaded_from_base64_encoded_data() -> None:
    dumped = "eyJwIjogImNHRjViRzloWkE9PSIsICJoIjogeyJrZXkiOiAiZG1Gc2RXVT0iLCAiZm9vIjogNDJ9fQ=="
    message = Message.load(dumped, "base64")

    assert message.payload == b"payload"
    assert message.headers == {"key": b"value", "foo": 42}


def test_message_can_be_loaded_from_json_encoded_data() -> None:
    dumped = '{"p": "cGF5bG9hZA==", "h": {"key": "dmFsdWU=", "foo": 42}}'
    message = Message.load(dumped, "json")

    assert message.payload == b"payload"
    assert message.headers == {"key": b"value", "foo": 42}
