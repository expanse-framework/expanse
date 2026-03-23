from typing import override

import msgspec

from expanse.messenger._serializers.serializer import Serializer
from expanse.types.messenger import Encoded


class MsgSpecSerializer(Serializer[msgspec.Struct]):
    name = "msgspec"

    @override
    def encode(self, obj: msgspec.Struct) -> Encoded:
        data = msgspec.json.encode(obj).decode()
        return {"data": data, "type": self._get_type(type(obj))}

    @override
    def decode(self, data: Encoded) -> msgspec.Struct:
        raw_data = data["data"]
        type_ = data["type"]

        return msgspec.json.decode(raw_data, type=self._import_type(type_))

    @override
    def supports(self, obj: msgspec.Struct | Encoded) -> bool:
        if isinstance(obj, dict):
            if "data" not in obj or "type" not in obj:
                return False

            type_ = self._import_type(obj["type"])

            return issubclass(type_, msgspec.Struct)

        return isinstance(obj, msgspec.Struct)
