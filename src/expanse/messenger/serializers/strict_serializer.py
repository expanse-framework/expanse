from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import MessageEncodingFailedError
from expanse.messenger.exceptions import UntrustedMessageTypeError
from expanse.serialization.serialization_manager import SerializationManager
from expanse.types.messenger import Encoded
from expanse.types.messenger import EncodedEnvelope
from expanse.types.messenger import Stamp


if TYPE_CHECKING:
    from expanse.messenger.trusted_collection import TrustedCollection
    from expanse.serialization.serializers.serializer import (
        Serializer as BaseSerializer,
    )


T = TypeVar("T")


class StrictSerializer(SerializerContract):
    """
    Encodes and decodes envelopes for transport.

    This serializer can only decode trusted types.
    """

    def __init__(
        self,
        trusted_collection: TrustedCollection,
        serialization_manager: SerializationManager | None = None,
    ) -> None:
        self._serialization_manager: SerializationManager = (
            serialization_manager or SerializationManager()
        )
        self._trusted_collection: TrustedCollection | None = trusted_collection

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
        message = self._decode(encoded_envelope["body"], encoded_envelope)
        raw_stamps: list[Encoded] = encoded_envelope["headers"].get("stamps", [])
        stamps: list[Stamp] = []
        for raw_stamp in raw_stamps:
            stamp: Stamp = self._decode(raw_stamp, encoded_envelope)
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

    def _decode(self, data: Encoded, encoded_envelope: EncodedEnvelope) -> Any:
        if not self._is_trusted(data["t"]):
            raise UntrustedMessageTypeError(
                f"Message of type '{data['t']}' is not trusted. Add it to the trusted collection.",
                encoded_envelope=encoded_envelope,
            )

        serializer = self._serialization_manager.serializer(data["s"])

        try:
            return serializer.decode(data)
        except Exception as e:
            raise MessageDecodingFailedError(
                f"Failed to decode message of type {data['t']}",
                encoded_envelope=encoded_envelope,
            ) from e

    def _is_trusted(self, type_name: str) -> bool:
        if self._trusted_collection is None:
            return True

        return self._trusted_collection.is_trusted_name(type_name)
