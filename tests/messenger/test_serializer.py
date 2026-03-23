from dataclasses import dataclass

import msgspec

from expanse.messenger.envelope import Envelope
from expanse.messenger.serializer import Serializer


@dataclass
class Foo:
    foo: str


class Bar(msgspec.Struct):
    bar: str


class MyStamp(msgspec.Struct):
    value: str


def test_serializer_supports_envelope_with_dataclass_message() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Foo(foo="bar"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["body"] == {
        "data": '{"foo":"bar"}',
        "type": "tests.messenger.test_serializer.Foo",
    }

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"


def test_serializer_supports_envelope_with_msgspec_message() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Bar(bar="baz"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["body"] == {
        "data": '{"bar":"baz"}',
        "type": "tests.messenger.test_serializer.Bar",
    }

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Bar)
    assert message.bar == "baz"


def test_serializer_serializes_envelope_with_stamps() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Foo(foo="bar")).with_stamps(MyStamp(value="test"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["headers"]["stamps"] == [
        {
            "data": '{"value":"test"}',
            "type": "tests.messenger.test_serializer.MyStamp",
        }
    ]

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"

    stamp = decoded_envelope.stamp(MyStamp)
    assert isinstance(stamp, MyStamp)
    assert stamp.value == "test"
