from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from pydantic import BaseModel

from expanse.messenger._serializers.serializer import Serializer


if TYPE_CHECKING:
    from expanse.types.messenger import Encoded


class PydanticSerializer(Serializer[BaseModel]):
    name = "pydantic"

    @override
    def encode(self, obj: BaseModel) -> Encoded:
        return {"data": obj.model_dump_json(), "type": self._get_type(type(obj))}

    @override
    def decode(self, data: Encoded) -> BaseModel:
        type_ = self._import_type(data["type"])

        return type_.model_validate_json(data["data"])

    @override
    def supports(self, obj: Any | Encoded) -> bool:
        if isinstance(obj, dict):
            if "data" not in obj or "type" not in obj:
                return False

            type_ = self._import_type(obj["type"])

            return issubclass(type_, BaseModel)

        return isinstance(obj, BaseModel)
