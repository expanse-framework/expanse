from __future__ import annotations

from typing import Any
from typing import override

from pydantic import BaseModel

from expanse.serialization.exceptions import UnauthorizedTypeDecodingError
from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name
from expanse.support._utils import string_to_class


class PydanticSerializer(Serializer[BaseModel]):
    name = "pydantic"

    @override
    def encode(self, obj: BaseModel) -> bytes:
        payload = obj.model_dump_json().encode()
        obj_type = class_to_name(type(obj)).encode()

        data = b""
        for part in (obj_type, payload):
            data += len(part).to_bytes(4, "big") + part

        return data

    @override
    def decode(self, data: bytes) -> BaseModel:
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

        return type_.model_validate_json(payload.decode())

    @override
    def supports(self, obj: Any) -> bool:
        return isinstance(obj, BaseModel)
