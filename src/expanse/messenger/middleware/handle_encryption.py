import hashlib

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgspec

from expanse.encryption.encryptor_factory import EncryptorFactory
from expanse.messenger.envelope import Envelope
from expanse.messenger.serializer import Serializer
from expanse.messenger.stamps.encrypted import EncryptedStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.sensitive import SensitiveStamp


if TYPE_CHECKING:
    from expanse.types.messenger import EncodedEnvelope


@dataclass(frozen=True, slots=True)
class EncryptedMessage:
    data: str


class HandleEncryption:
    """
    Middleware to encrypt/decrypt messages upon sending and reception.
    """

    def __init__(self, encryption: EncryptorFactory, serializer: Serializer) -> None:
        self._encryption: EncryptorFactory = encryption
        self._serializer: Serializer = serializer

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        if envelope.has_stamp(ReceivedStamp):
            if not envelope.has_stamp(SensitiveStamp):
                return await next_call(envelope)

            return await next_call(self._decrypt(envelope))

        if not envelope.has_stamp(SensitiveStamp):
            return await next_call(envelope)

        return await next_call(self._encrypt(envelope))

    def _encrypt(self, envelope: Envelope) -> Envelope:
        # We need to serialize the message before encrypting it.
        encoded_envelope = self._serializer.encode(envelope)
        payload = msgspec.json.encode(encoded_envelope).decode()
        label = hashlib.sha256(encoded_envelope["body"]["t"].encode()).hexdigest()

        encryptor = self._encryption.make(label=label.encode())
        encrypted_payload = encryptor.encrypt(payload)

        # Create a new envelope with the encrypted message
        # and the same stamps as the original envelope.
        message = EncryptedMessage(data=encrypted_payload)

        return Envelope.wrap(
            message, stamps=[*envelope.stamps(), EncryptedStamp(label=label)]
        )

    def _decrypt(self, envelope: Envelope) -> Envelope:
        stamp = envelope.stamp(EncryptedStamp)
        assert stamp is not None, "Envelope must have an EncryptedStamp to be decrypted"

        message = envelope.open()
        assert isinstance(message, EncryptedMessage)

        encryptor = self._encryption.make(label=stamp.label.encode())
        decrypted_payload = encryptor.decrypt(message.data)

        decoded_envelope: EncodedEnvelope = msgspec.json.decode(decrypted_payload)

        return self._serializer.decode(decoded_envelope).with_stamps(
            *[s for s in envelope.stamps() if not isinstance(s, EncryptedStamp)]
        )
