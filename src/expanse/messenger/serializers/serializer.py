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
from expanse.serialization.exceptions import UnauthorizedTypeDecodingError
from expanse.types.messenger import EncodedEnvelope
from expanse.types.messenger import EncodedEnvelopeHeaders
from expanse.types.messenger import Stamp


if TYPE_CHECKING:
    from expanse.serialization.serialization_manager import SerializationManager
    from expanse.serialization.serializers.serializer import (
        Serializer as BaseSerializer,
    )


T = TypeVar("T")


class Serializer(SerializerContract):
    """
    Encodes and decodes envelopes for transport.
    """

    def __init__(self, serialization_manager: SerializationManager) -> None:
        self._serialization_manager: SerializationManager = serialization_manager

    @override
    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        message = envelope.open()
        body = self._encode(message)
        headers: EncodedEnvelopeHeaders = {}

        if envelope.is_stamped():
            stamps: list[Stamp] = envelope.stamps()
            headers["stamps"] = [self._encode(s) for s in stamps]

        return EncodedEnvelope(body=body, headers=headers)

    @override
    def decode(self, encoded_envelope: EncodedEnvelope) -> Envelope:
        try:
            message = self._decode(encoded_envelope["body"])
        except UnauthorizedTypeDecodingError as e:
            raise UntrustedMessageTypeError(
                str(e), encoded_envelope=encoded_envelope
            ) from e
        except Exception as e:
            raise MessageDecodingFailedError(
                "Failed to decode message", encoded_envelope=encoded_envelope
            ) from e

        raw_stamps: list[bytes] = encoded_envelope["headers"].get("stamps", [])
        stamps: list[Stamp] = []
        for raw_stamp in raw_stamps:
            try:
                stamp: Stamp = self._decode(raw_stamp)
                stamps.append(stamp)
            except Exception:  # noqa: BLE001 - any decode failure is a decoding error
                raise MessageDecodingFailedError(
                    "Failed to decode stamp",
                    encoded_envelope=encoded_envelope,
                )

        return Envelope.wrap(message, stamps)

    def _encode(self, obj: Any) -> bytes:
        serializer: BaseSerializer[Any] = self._serialization_manager.serializer_for(
            obj
        )

        try:
            return self._wrap(serializer.name, serializer.encode(obj))
        except Exception as e:
            raise MessageEncodingFailedError(
                f"Failed to encode message of type {type(obj)}"
            ) from e

    def _decode(self, data: bytes) -> Any:
        serializer_name, encoded_data = self._unwrap(data)
        serializer = self._serialization_manager.serializer(serializer_name)

        return serializer.decode(encoded_data)

    @classmethod
    def _wrap(cls, name: str, data: bytes) -> bytes:
        """
        Wrap the serialized data by prefixing it with the serializer name.

        The prefix consists of the length of the serializer name (4 bytes, big-endian) followed by the serializer name itself.

        :param name: The name of the serializer.
        :param data: The serialized data to be wrapped.
        :return: the wrapped serialized data as bytes.
        """
        name_bytes = name.encode()
        name_length = len(name_bytes).to_bytes(4, "big")
        return name_length + name_bytes + data

    @classmethod
    def _unwrap(cls, data: bytes) -> tuple[str, bytes]:
        """
        Unwrap the serialized data by extracting the serializer name and the actual serialized data.

        :param data: The wrapped serialized data.
        :return: A tuple containing the serializer name and the actual serialized data.
        """
        name_length = int.from_bytes(data[:4], "big")
        name = data[4 : 4 + name_length].decode()
        actual_data = data[4 + name_length :]
        return name, actual_data
