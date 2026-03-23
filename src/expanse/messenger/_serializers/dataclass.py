from typing import Any
from typing import ClassVar
from typing import Protocol
from typing import override

import msgspec

from expanse.messenger._serializers.serializer import Serializer
from expanse.types.messenger import Encoded


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


class DataclassSerializer(Serializer[Dataclass]):
    name = "dataclass"

    @override
    def encode(self, obj: Dataclass) -> Encoded:
        return {
            "data": msgspec.json.encode(obj).decode(),
            "type": self._get_type(type(obj)),
        }

    @override
    def decode(self, data: Encoded) -> Dataclass:
        raw_data = data["data"]

        type_ = self._import_type(data["type"])

        return type_(**msgspec.json.decode(raw_data))

    @override
    def supports(self, obj: Any | Encoded) -> bool:
        if isinstance(obj, dict):
            if "data" not in obj or "type" not in obj:
                return False

            type_ = self._import_type(obj["type"])

            return hasattr(type_, "__dataclass_fields__")

        return hasattr(obj, "__dataclass_fields__")
