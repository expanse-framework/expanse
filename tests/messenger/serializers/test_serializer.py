from dataclasses import dataclass

import pytest

from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import UntrustedMessageTypeError
from expanse.messenger.serializers.serializer import Serializer
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer


@dataclass
class Foo:
    value: str


def _make_serializer(allowed: set[str] | None = None) -> Serializer:
    serialization_manager = SerializationManager()
    dataclass_serializer = DataclassSerializer()
    if allowed is not None:
        dataclass_serializer = dataclass_serializer.restrict(allowed)
    serialization_manager.register_serializer(dataclass_serializer)

    return Serializer(serialization_manager)


def test_round_trip_without_restrictions() -> None:
    serializer = _make_serializer()

    encoded = serializer.encode(Envelope.wrap(Foo(value="bar")))
    decoded = serializer.decode(encoded)

    assert decoded.open() == Foo(value="bar")


def test_decode_raises_untrusted_message_type_error_for_a_disallowed_type() -> None:
    serializer = _make_serializer(allowed=set())

    encoded = serializer.encode(Envelope.wrap(Foo(value="bar")))

    with pytest.raises(UntrustedMessageTypeError) as exc_info:
        serializer.decode(encoded)

    # `UntrustedMessageTypeError` is a `MessageDecodingFailedError`, so it is
    # caught by the transports and routed through the failure-decoding pipeline.
    assert isinstance(exc_info.value, MessageDecodingFailedError)
    assert exc_info.value.encoded_envelope == encoded


def test_decode_raises_message_decoding_failed_error_for_an_unknown_serializer() -> (
    None
):
    serializer = _make_serializer()

    encoded = serializer.encode(Envelope.wrap(Foo(value="bar")))
    body = encoded["body"]
    name_length = int.from_bytes(body[:4], "big")
    tampered = (5).to_bytes(4, "big") + b"other" + body[4 + name_length :]
    encoded["body"] = tampered

    with pytest.raises(MessageDecodingFailedError):
        serializer.decode(encoded)
