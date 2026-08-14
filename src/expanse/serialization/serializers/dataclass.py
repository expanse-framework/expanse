from typing import Any
from typing import ClassVar
from typing import Protocol
from typing import override

import msgspec

from expanse.serialization.exceptions import UnauthorizedTypeDecodingError
from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name
from expanse.support._utils import string_to_class


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


class DataclassSerializer(Serializer[Dataclass]):
    name = "dataclass"

    @override
    def encode(self, obj: Dataclass) -> bytes:
        payload = msgspec.json.encode(obj)
        obj_type = class_to_name(type(obj)).encode()

        data = b""
        for part in (obj_type, payload):
            data += len(part).to_bytes(4, "big") + part

        return data

    @override
    def decode(self, data: bytes) -> Dataclass:
        raw_data = data

        parts = []
        while raw_data:
            part_len = int.from_bytes(raw_data[:4], "big")
            raw_data = raw_data[4:]
            part = raw_data[:part_len]
            raw_data = raw_data[part_len:]
            parts.append(part)

        raw_type, payload = parts
        type_name = raw_type.decode()

        if not self.is_allowed(type_name):
            raise UnauthorizedTypeDecodingError(
                f"Type {type_name} is not allowed for deserialization"
            )

        type_ = string_to_class(type_name)

        return msgspec.json.decode(payload, type=type_)

    @override
    def supports(self, obj: Any) -> bool:
        return hasattr(obj, "__dataclass_fields__")
