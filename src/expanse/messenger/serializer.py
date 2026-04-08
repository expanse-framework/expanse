from typing import Any
from typing import TypeVar

from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import MessageEncodingFailedError
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.serializer import Serializer as BaseSerializer
from expanse.types.messenger import Encoded
from expanse.types.messenger import EncodedEnvelope
from expanse.types.messenger import Stamp


T = TypeVar("T")


class Serializer:
    def __init__(
        self, serialization_manager: SerializationManager | None = None
    ) -> None:
        self._serialization_manager: SerializationManager = (
            serialization_manager or SerializationManager()
        )

    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        message = envelope.open()
        body = self._encode(message)
        headers: dict[str, Any] = {}

        if envelope.is_stamped():
            stamps: list[Stamp] = envelope.stamps()
            headers["stamps"] = [self._encode(s) for s in stamps]

        return EncodedEnvelope(body=body, headers=headers)

    def decode(self, encoded: EncodedEnvelope) -> Envelope:
        message = self._decode(encoded["body"])
        raw_stamps: list[Encoded] = encoded["headers"].get("stamps", [])
        stamps: list[Stamp] = []
        for raw_stamp in raw_stamps:
            stamp: Stamp = self._decode(raw_stamp)
            stamps.append(stamp)

        return Envelope.wrap(message, stamps)

    def _encode(self, obj: Any) -> Encoded:
        serializer: BaseSerializer[Any] = self._serialization_manager.serializer_for(
            obj
        )

        try:
            return serializer.encode(obj)
        except Exception as e:
            raise MessageEncodingFailedError(
                f"Failed to encode message of type {type(obj)}"
            ) from e

    def _decode(self, data: Encoded) -> Any:
        serializer = self._serialization_manager.serializer(data["s"])

        try:
            return serializer.decode(data)
        except Exception as e:
            raise MessageDecodingFailedError(
                f"Failed to decode message of type {data['t']}"
            ) from e
