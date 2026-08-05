from dataclasses import dataclass

import pytest

from expanse.core.application import Application
from expanse.encryption.encryptor_factory import EncryptorFactory
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.messenger.envelope import Envelope
from expanse.messenger.middleware.handle_encryption import EncryptedMessage
from expanse.messenger.middleware.handle_encryption import HandleEncryption
from expanse.messenger.serializers.serializer import Serializer
from expanse.messenger.stamps.encrypted import EncryptedStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.sensitive import SensitiveStamp


@dataclass(frozen=True)
class MyMessage:
    value: str


async def next_call(envelope: Envelope) -> Envelope:
    return envelope


@pytest.fixture()
def encryption() -> EncryptorFactory:
    return EncryptorFactory(KeyChain([Key(b"k" * 32)]), salt=b"s" * 32)


async def test_middleware_handles_encryption_and_decryption_properly(
    encryption: EncryptorFactory,
) -> None:
    serializer = Serializer()
    middleware = HandleEncryption(encryption, serializer)

    envelope = Envelope.wrap(
        MyMessage(value="Hello, world!"), stamps=[SensitiveStamp()]
    )

    encrypted_envelope = await middleware.handle(envelope, next_call)

    # The envelope should now have an EncryptedStamp with the correct label
    stamp = encrypted_envelope.stamp(EncryptedStamp)
    assert stamp is not None

    # The envelope should now be wrapped in an encrypted envelope
    encrypted_message = encrypted_envelope.open()
    assert isinstance(encrypted_message, EncryptedMessage)
    assert encrypted_message.data != "Hello, world!"

    # Mark the envelope as received to trigger decryption
    decrypted_envelope = await middleware.handle(
        encrypted_envelope.with_stamps(ReceivedStamp()), next_call
    )
    decrypted_message = decrypted_envelope.open()
    assert isinstance(decrypted_message, MyMessage)
    assert decrypted_message.value == "Hello, world!"


async def test_middleware_does_not_encrypt_envelope_without_sensitive_stamp(
    app: Application, encryption: EncryptorFactory
) -> None:
    app.config["app.secret_key"] = "k" * 32
    app.config["encryption"] = {
        "cipher": "aes-256-gcm",
        "salt": "s" * 32,
    }
    serializer = Serializer()
    middleware = HandleEncryption(encryption, serializer)

    envelope = Envelope.wrap(MyMessage(value="Hello, world!"))

    processed_envelope = await middleware.handle(envelope, next_call)

    # The envelope should not have an EncryptedStamp
    assert not processed_envelope.has_stamp(EncryptedStamp)

    # The message should be unchanged
    message = processed_envelope.open()
    assert isinstance(message, MyMessage)
    assert message.value == "Hello, world!"
