from expanse.encryption.message import Message


def test_message_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value"})
    dumped = message.dump()

    assert dumped == {"p": "cGF5bG9hZA==", "h": {"key": "value"}}


def test_message_with_null_payload_dumpable() -> None:
    message = Message(None)
    dumped = message.dump()

    assert dumped == {"p": None, "h": {}}


def test_message_with_bytes_header_value_is_dumpable() -> None:
    message = Message(b"payload", {"key": "value", "bytes": b"bytes"})
    dumped = message.dump()

    assert dumped == {"p": "cGF5bG9hZA==", "h": {"key": "value", "bytes": "Ynl0ZXM="}}


def test_message_is_representable() -> None:
    message = Message(b"payload", {"key": "value"})

    assert repr(message) == "Message(b'payload', {'key': 'value'})"
