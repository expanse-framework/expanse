from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgspec

from pydantic import BaseModel

from expanse.serialization.serializers.msgspec import MsgSpecSerializer


if TYPE_CHECKING:
    from expanse.types.serialization import Encoded


class SimpleStruct(msgspec.Struct):
    name: str
    age: int


class NestedStruct(msgspec.Struct):
    label: str
    values: list[int]


@dataclass
class NotAStruct:
    value: str


class AlsoNotAStruct(BaseModel):
    value: str


def test_encode_msgspec_struct() -> None:
    serializer = MsgSpecSerializer()
    obj = SimpleStruct(name="Alice", age=30)

    encoded = serializer.encode(obj)

    assert encoded["d"] == '{"name":"Alice","age":30}'
    assert encoded["t"] == "tests.serialization.serializers.test_msgspec.SimpleStruct"
    assert encoded["s"] == "msgspec"


def test_decode_msgspec_struct() -> None:
    serializer = MsgSpecSerializer()
    encoded: Encoded = {
        "d": '{"name":"Alice","age":30}',
        "t": "tests.serialization.serializers.test_msgspec.SimpleStruct",
        "s": "msgspec",
    }

    obj = serializer.decode(encoded)

    assert isinstance(obj, SimpleStruct)
    assert obj.name == "Alice"
    assert obj.age == 30


def test_encode_decode_roundtrip() -> None:
    serializer = MsgSpecSerializer()
    original = NestedStruct(label="test", values=[1, 2, 3])

    encoded = serializer.encode(original)
    decoded = serializer.decode(encoded)

    assert isinstance(decoded, NestedStruct)
    assert decoded.label == original.label
    assert decoded.values == original.values


def test_supports_msgspec_struct() -> None:
    serializer = MsgSpecSerializer()

    assert serializer.supports(SimpleStruct(name="Alice", age=30))


def test_does_not_support_dataclass() -> None:
    serializer = MsgSpecSerializer()

    assert not serializer.supports(NotAStruct(value="test"))


def test_does_not_support_pydantic_model() -> None:
    serializer = MsgSpecSerializer()

    assert not serializer.supports(AlsoNotAStruct(value="test"))


def test_does_not_support_plain_object() -> None:
    serializer = MsgSpecSerializer()

    assert not serializer.supports(42)


def test_name() -> None:
    assert MsgSpecSerializer.name == "msgspec"
