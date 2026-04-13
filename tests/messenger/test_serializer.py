from dataclasses import dataclass

import msgspec

from pydantic import BaseModel

from expanse.messenger.envelope import Envelope
from expanse.messenger.serializer import Serializer


@dataclass
class Foo:
    foo: str


class Bar(msgspec.Struct):
    bar: str


class Baz(BaseModel):
    baz: str


class MyStamp(msgspec.Struct):
    value: str


def test_serializer_supports_envelope_with_dataclass_message() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Foo(foo="bar"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["body"] == {
        "d": '{"foo":"bar"}',
        "t": "tests.messenger.test_serializer.Foo",
        "s": "dataclass",
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
        "d": '{"bar":"baz"}',
        "t": "tests.messenger.test_serializer.Bar",
        "s": "msgspec",
    }

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Bar)
    assert message.bar == "baz"


def test_serializer_supports_envelope_with_pydantic_message() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Baz(baz="qux"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["body"] == {
        "d": '{"baz":"qux"}',
        "t": "tests.messenger.test_serializer.Baz",
        "s": "pydantic",
    }

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Baz)
    assert message.baz == "qux"


def test_serializer_serializes_envelope_with_stamps() -> None:
    serializer = Serializer()

    envelope = Envelope.wrap(Foo(foo="bar")).with_stamps(MyStamp(value="test"))
    encoded_envelope = serializer.encode(envelope)

    assert encoded_envelope["headers"]["stamps"] == [
        {
            "d": '{"value":"test"}',
            "t": "tests.messenger.test_serializer.MyStamp",
            "s": "msgspec",
        }
    ]

    decoded_envelope = serializer.decode(encoded_envelope)
    message = decoded_envelope.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"

    stamp = decoded_envelope.stamp(MyStamp)
    assert isinstance(stamp, MyStamp)
    assert stamp.value == "test"
