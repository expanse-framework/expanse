from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import msgspec

from expanse.contracts.messenger.serializer import Serializer
from expanse.encryption.encryption_manager import EncryptionManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.encrypted import EncryptedStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.sensitive import SensitiveStamp
from expanse.support._utils import class_to_name
from expanse.types.messenger import EncodedEnvelope


@dataclass(frozen=True, slots=True)
class EncryptedMessage:
    data: str


class HandleEncryption:
    """
    Middleware to encrypt/decrypt messages upon sending and reception.
    """

    _purpose: str = "expanse/messenger/encryption"

    def __init__(self, encryption: EncryptionManager, serializer: Serializer) -> None:
        self._encryption: EncryptionManager = encryption
        self._serializer: Serializer = serializer

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        if envelope.has_stamp(ReceivedStamp):
            if not envelope.has_stamp(EncryptedStamp):
                return await next_call(envelope)

            return await next_call(self._decrypt(envelope))

        if not envelope.has_stamp(SensitiveStamp):
            return await next_call(envelope)

        return await next_call(self._encrypt(envelope))

    def _encrypt(self, envelope: Envelope) -> Envelope:
        # We need to serialize the message before encrypting it.
        encoded_envelope = self._serializer.encode(envelope)
        payload = msgspec.json.encode(encoded_envelope).decode()
        purpose = f"{self._purpose}/{class_to_name(type(envelope.open()))}"
        encrypted_payload = self._encryption.encrypt(payload, purpose=purpose)

        # Create a new envelope with the encrypted message
        # and the same stamps as the original envelope.
        message = EncryptedMessage(data=encrypted_payload)

        return Envelope.wrap(message, stamps=[EncryptedStamp(purpose=purpose)])

    def _decrypt(self, envelope: Envelope) -> Envelope:
        stamp = envelope.stamp(EncryptedStamp)
        assert stamp is not None, "Envelope must have an EncryptedStamp to be decrypted"

        message = envelope.open()
        assert isinstance(message, EncryptedMessage)

        decrypted_payload = self._encryption.decrypt(
            message.data, purpose=stamp.purpose
        )

        decoded_envelope = msgspec.json.decode(
            decrypted_payload.encode(),
            type=EncodedEnvelope,
        )

        all_stamps: list[Any] = envelope.stamps()
        return self._serializer.decode(decoded_envelope).with_stamps(
            *[s for s in all_stamps if not isinstance(s, EncryptedStamp)]
        )
