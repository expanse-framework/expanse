from typing import Any
from typing import override

import msgspec

from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name
from expanse.support._utils import string_to_class
from expanse.types.serialization import Encoded


class MsgSpecSerializer(Serializer[msgspec.Struct]):
    name = "msgspec"

    @override
    def encode(self, obj: msgspec.Struct) -> Encoded:
        data = msgspec.json.encode(obj).decode()
        return {"d": data, "t": class_to_name(type(obj)), "s": self.name}

    @override
    def decode(self, data: Encoded) -> msgspec.Struct:
        raw_data = data["d"]
        type_ = data["t"]

        return msgspec.json.decode(raw_data, type=string_to_class(type_))

    @override
    def supports(self, obj: Any) -> bool:
        return isinstance(obj, msgspec.Struct)
