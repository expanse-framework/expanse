from typing import Any
from typing import TypeVar

from expanse.messenger._serializers.dataclass import DataclassSerializer
from expanse.messenger._serializers.msgspec import MsgSpecSerializer
from expanse.messenger._serializers.pydantic import PydanticSerializer
from expanse.messenger._serializers.serializer import Serializer as BaseSerializer
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import MessageEncodingFailedError
from expanse.messenger.exceptions import NoSerializerRegisteredError
from expanse.types.messenger import Encoded
from expanse.types.messenger import EncodedEnvelope
from expanse.types.messenger import Stamp


T = TypeVar("T")


class Serializer:
    def __init__(self) -> None:
        self._serializers: dict[str, BaseSerializer[Any]] = {}

        self.register(MsgSpecSerializer(), DataclassSerializer(), PydanticSerializer())

    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        if not self._serializers:
            raise NoSerializerRegisteredError("No serializers registered")

        message = envelope.open()
        body = self._encode(message)
        headers: dict[str, Any] = {
            "stamps": {
                stamp_type.__name__: self._encode(envelope.stamp(stamp_type))
                for stamp_type in envelope._stamps
            },
        }

        if envelope.is_stamped():
            headers["stamps"] = [self._encode(stamp) for stamp in envelope.stamps]

        return EncodedEnvelope(body=body, headers=headers)

    def decode(self, encoded: EncodedEnvelope) -> Envelope:
        if not self._serializers:
            raise NoSerializerRegisteredError("No serializers registered")

        message = self._decode(encoded["body"])
        raw_stamps: list[Encoded] = encoded["headers"].get("stamps", [])
        stamps: list[Stamp] = []
        for raw_stamp in raw_stamps:
            stamp: Stamp = self._decode(raw_stamp)
            stamps.append(stamp)

        return Envelope.wrap(message, stamps)

    def register(self, *serializers: BaseSerializer[Any]) -> None:
        for serializer in serializers:
            self._serializers[serializer.name] = serializer

    def _encode(self, obj: Any) -> Encoded:
        serializer: BaseSerializer[Any] | None = None
        for _, base_serializer in self._serializers.items():
            if base_serializer.supports(obj):
                serializer = base_serializer
                break

        if serializer is None:
            raise NoSerializerRegisteredError(
                f"No serializer registered for message type {type(obj)}"
            )

        try:
            return serializer.encode(obj)
        except Exception as e:
            raise MessageEncodingFailedError(
                f"Failed to encode message of type {type(obj)}"
            ) from e

    def _decode(self, data: Encoded) -> Any:
        if not self._serializers:
            raise NoSerializerRegisteredError("No serializers registered")

        for _, serializer in self._serializers.items():
            if serializer.supports(data):
                try:
                    return serializer.decode(data)
                except Exception as e:
                    raise MessageDecodingFailedError(
                        f"Failed to decode message of type {data['type']}"
                    ) from e
        else:
            raise NoSerializerRegisteredError(
                f"No serializer registered for message type {data['type']}"
            )
