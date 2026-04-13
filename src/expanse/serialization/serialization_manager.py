from typing import Any

from expanse.serialization.exceptions import UnconfiguredSerializerError
from expanse.serialization.exceptions import UnserializableObjectError
from expanse.serialization.serializers.dataclass import DataclassSerializer
from expanse.serialization.serializers.msgspec import MsgSpecSerializer
from expanse.serialization.serializers.pydantic import PydanticSerializer
from expanse.serialization.serializers.serializer import Serializer


class SerializationManager:
    def __init__(self) -> None:
        self._serializers: dict[str, Serializer[Any]] = {
            "msgspec": MsgSpecSerializer(),
            "dataclass": DataclassSerializer(),
            "pydantic": PydanticSerializer(),
        }

    def serializer(self, name: str) -> Serializer[Any]:
        if name not in self._serializers:
            raise UnconfiguredSerializerError(
                f"No serializer configured with name {name}"
            )

        return self._serializers[name]

    def serializer_for(self, obj: Any) -> Serializer[Any]:
        for serializer in self._serializers.values():
            if serializer.supports(obj):
                return serializer

        raise UnserializableObjectError(
            f"Object of type {type(obj)} is not serializable"
        )
