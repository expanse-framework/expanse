from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgspec

from pydantic import BaseModel

from expanse.serialization.serializers.pydantic import PydanticSerializer


if TYPE_CHECKING:
    from expanse.types.serialization import Encoded


class SimpleModel(BaseModel):
    name: str
    age: int


class NestedModel(BaseModel):
    label: str
    values: list[int]


@dataclass
class NotAModel:
    value: str


class AlsoNotAModel(msgspec.Struct):
    value: str


def test_encode_pydantic_model() -> None:
    serializer = PydanticSerializer()
    obj = SimpleModel(name="Alice", age=30)

    encoded = serializer.encode(obj)

    assert encoded["d"] == '{"name":"Alice","age":30}'
    assert encoded["t"] == "tests.serialization.serializers.test_pydantic.SimpleModel"
    assert encoded["s"] == "pydantic"


def test_decode_pydantic_model() -> None:
    serializer = PydanticSerializer()
    encoded: Encoded = {
        "d": '{"name":"Alice","age":30}',
        "t": "tests.serialization.serializers.test_pydantic.SimpleModel",
        "s": "pydantic",
    }

    obj = serializer.decode(encoded)

    assert isinstance(obj, SimpleModel)
    assert obj.name == "Alice"
    assert obj.age == 30


def test_encode_decode_roundtrip() -> None:
    serializer = PydanticSerializer()
    original = NestedModel(label="test", values=[1, 2, 3])

    encoded = serializer.encode(original)
    decoded = serializer.decode(encoded)

    assert isinstance(decoded, NestedModel)
    assert decoded.label == original.label
    assert decoded.values == original.values


def test_supports_pydantic_model() -> None:
    serializer = PydanticSerializer()

    assert serializer.supports(SimpleModel(name="Alice", age=30))


def test_does_not_support_dataclass() -> None:
    serializer = PydanticSerializer()

    assert not serializer.supports(NotAModel(value="test"))


def test_does_not_support_msgspec_struct() -> None:
    serializer = PydanticSerializer()

    assert not serializer.supports(AlsoNotAModel(value="test"))


def test_does_not_support_plain_object() -> None:
    serializer = PydanticSerializer()

    assert not serializer.supports({"key": "value"})


def test_name() -> None:
    assert PydanticSerializer.name == "pydantic"
