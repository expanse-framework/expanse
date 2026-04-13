from dataclasses import dataclass

import msgspec

from pydantic import BaseModel

from expanse.serialization.serializers.dataclass import DataclassSerializer
from expanse.types.serialization import Encoded


@dataclass
class SimpleDataclass:
    name: str
    age: int


@dataclass
class NestedDataclass:
    label: str
    values: list[int]


class NotADataclass(msgspec.Struct):
    value: str


class AlsoNotADataclass(BaseModel):
    value: str


def test_encode_dataclass() -> None:
    serializer = DataclassSerializer()
    obj = SimpleDataclass(name="Alice", age=30)

    encoded = serializer.encode(obj)

    assert encoded["d"] == '{"name":"Alice","age":30}'
    assert (
        encoded["t"] == "tests.serialization.serializers.test_dataclass.SimpleDataclass"
    )
    assert encoded["s"] == "dataclass"


def test_decode_dataclass() -> None:
    serializer = DataclassSerializer()
    encoded: Encoded = {
        "d": '{"name":"Alice","age":30}',
        "t": "tests.serialization.serializers.test_dataclass.SimpleDataclass",
        "s": "dataclass",
    }

    obj = serializer.decode(encoded)

    assert isinstance(obj, SimpleDataclass)
    assert obj.name == "Alice"
    assert obj.age == 30


def test_encode_decode_roundtrip() -> None:
    serializer = DataclassSerializer()
    original = NestedDataclass(label="test", values=[1, 2, 3])

    encoded = serializer.encode(original)
    decoded = serializer.decode(encoded)

    assert isinstance(decoded, NestedDataclass)
    assert decoded.label == original.label
    assert decoded.values == original.values


def test_supports_dataclass() -> None:
    serializer = DataclassSerializer()

    assert serializer.supports(SimpleDataclass(name="Alice", age=30))


def test_does_not_support_msgspec_struct() -> None:
    serializer = DataclassSerializer()

    assert not serializer.supports(NotADataclass(value="test"))


def test_does_not_support_pydantic_model() -> None:
    serializer = DataclassSerializer()

    assert not serializer.supports(AlsoNotADataclass(value="test"))


def test_does_not_support_plain_object() -> None:
    serializer = DataclassSerializer()

    assert not serializer.supports("a string")


def test_name() -> None:
    assert DataclassSerializer.name == "dataclass"
