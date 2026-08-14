from dataclasses import dataclass

import msgspec
import pytest

from pydantic import BaseModel

from expanse.serialization.exceptions import UnconfiguredSerializerError
from expanse.serialization.exceptions import UnserializableObjectError
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer
from expanse.serialization.serializers.msgspec import MsgSpecSerializer
from expanse.serialization.serializers.pydantic import PydanticSerializer


@dataclass
class MyDataclass:
    value: str


class MyStruct(msgspec.Struct):
    value: str


class MyModel(BaseModel):
    value: str


@pytest.fixture()
def manager() -> SerializationManager:
    manager = SerializationManager()
    manager.register_serializer(DataclassSerializer())
    manager.register_serializer(MsgSpecSerializer())
    manager.register_serializer(PydanticSerializer())

    return manager


def test_serializer_returns_registered_serializer_by_name(
    manager: SerializationManager,
) -> None:
    assert isinstance(manager.serializer("dataclass"), DataclassSerializer)
    assert isinstance(manager.serializer("msgspec"), MsgSpecSerializer)
    assert isinstance(manager.serializer("pydantic"), PydanticSerializer)


def test_serializer_raises_for_unconfigured_name(manager: SerializationManager) -> None:
    with pytest.raises(UnconfiguredSerializerError, match="unknown"):
        manager.serializer("unknown")


def test_serializer_for_returns_dataclass_serializer(
    manager: SerializationManager,
) -> None:
    serializer = manager.serializer_for(MyDataclass(value="test"))

    assert isinstance(serializer, DataclassSerializer)


def test_serializer_for_returns_msgspec_serializer(
    manager: SerializationManager,
) -> None:
    serializer = manager.serializer_for(MyStruct(value="test"))

    assert isinstance(serializer, MsgSpecSerializer)


def test_serializer_for_returns_pydantic_serializer(
    manager: SerializationManager,
) -> None:
    serializer = manager.serializer_for(MyModel(value="test"))

    assert isinstance(serializer, PydanticSerializer)


def test_serializer_for_raises_for_unsupported_object(
    manager: SerializationManager,
) -> None:
    with pytest.raises(UnserializableObjectError, match="str"):
        manager.serializer_for("not serializable")
