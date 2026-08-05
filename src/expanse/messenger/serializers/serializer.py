from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import MessageEncodingFailedError
from expanse.serialization.serialization_manager import SerializationManager
from expanse.types.messenger import Encoded
from expanse.types.messenger import EncodedEnvelope
from expanse.types.messenger import Stamp


if TYPE_CHECKING:
    from expanse.serialization.serializers.serializer import (
        Serializer as BaseSerializer,
    )


T = TypeVar("T")


class Serializer(SerializerContract):
    """
    Encodes and decodes envelopes for transport.
    """

    def __init__(
        self, serialization_manager: SerializationManager | None = None
    ) -> None:
        self._serialization_manager: SerializationManager = (
            serialization_manager or SerializationManager()
        )

    @override
    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        message = envelope.open()
        body = self._encode(message)
        headers: dict[str, Any] = {}

        if envelope.is_stamped():
            stamps: list[Stamp] = envelope.stamps()
            headers["stamps"] = [self._encode(s) for s in stamps]

        return EncodedEnvelope(body=body, headers=headers)

    @override
    def decode(self, encoded_envelope: EncodedEnvelope) -> Envelope:
        message = self._decode(encoded_envelope["body"])
        raw_stamps: list[Encoded] = encoded_envelope["headers"].get("stamps", [])
        stamps: list[Stamp] = []
        for raw_stamp in raw_stamps:
            try:
                stamp: Stamp = self._decode(raw_stamp)
                stamps.append(stamp)
            except Exception:
                raise MessageDecodingFailedError(
                    f"Failed to decode stamp of type {raw_stamp['t']}",
                    encoded_envelope=encoded_envelope,
                )

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

        return serializer.decode(data)
