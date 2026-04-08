from typing import Any
from typing import ClassVar
from typing import Protocol
from typing import override

import msgspec

from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name
from expanse.support._utils import string_to_class
from expanse.types.serialization import Encoded


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


class DataclassSerializer(Serializer[Dataclass]):
    name = "dataclass"

    @override
    def encode(self, obj: Dataclass) -> Encoded:
        return {
            "d": msgspec.json.encode(obj).decode(),
            "t": class_to_name(type(obj)),
            "s": self.name,
        }

    @override
    def decode(self, data: Encoded) -> Dataclass:
        raw_data = data["d"]

        type_ = string_to_class(data["t"])

        return type_(**msgspec.json.decode(raw_data))

    @override
    def supports(self, obj: Any) -> bool:
        return hasattr(obj, "__dataclass_fields__")
