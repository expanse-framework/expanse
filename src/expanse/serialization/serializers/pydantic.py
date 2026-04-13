from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from pydantic import BaseModel

from expanse.serialization.serializers.serializer import Serializer
from expanse.support._utils import class_to_name
from expanse.support._utils import string_to_class


if TYPE_CHECKING:
    from expanse.types.serialization import Encoded


class PydanticSerializer(Serializer[BaseModel]):
    name = "pydantic"

    @override
    def encode(self, obj: BaseModel) -> Encoded:
        return {
            "d": obj.model_dump_json(),
            "t": class_to_name(type(obj)),
            "s": self.name,
        }

    @override
    def decode(self, data: Encoded) -> BaseModel:
        type_ = string_to_class(data["t"])

        return type_.model_validate_json(data["d"])

    @override
    def supports(self, obj: Any) -> bool:
        return isinstance(obj, BaseModel)
