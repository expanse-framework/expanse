from dataclasses import dataclass

import pytest

from expanse.contracts.encryption.signer import Signer as SignerContract
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.signer import Signer
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.serializers.serializer import Serializer as InnerSerializer
from expanse.messenger.serializers.signing_serializer import SigningSerializer
from expanse.serialization.serialization_manager import SerializationManager
from expanse.serialization.serializers.dataclass import DataclassSerializer
from expanse.types.messenger import EncodedEnvelope


@dataclass
class Foo:
    foo: str


class FakeSigner(SignerContract):
    def __init__(self, signature: bytes = b"\x01\x02\x03", verifies: bool = True):
        self.signature: bytes = signature
        self.verifies: bool = verifies
        self.sign_calls: list[tuple[bytes, bytes | str | None]] = []
        self.verify_calls: list[tuple[bytes, bytes, bytes | str | None]] = []

    def sign(self, data: bytes | str, purpose: bytes | str | None = None) -> bytes:
        if isinstance(data, str):
            data = data.encode()

        self.sign_calls.append((data, purpose))

        return self.signature

    def verify(
        self, data: bytes, signature: bytes, purpose: bytes | str | None = None
    ) -> bool:
        self.verify_calls.append((data, signature, purpose))

        return self.verifies


def _make_encoded_envelope(inner: InnerSerializer) -> EncodedEnvelope:
    return inner.encode(Envelope.wrap(Foo(foo="bar")))


@pytest.fixture()
def inner_serializer() -> InnerSerializer:
    serialization_manager = SerializationManager()
    serialization_manager.register_serializer(DataclassSerializer())

    return InnerSerializer(serialization_manager)


def test_encode_adds_a_hex_encoded_signature_header(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner(signature=b"\x01\x02\x03")
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))

    assert encoded["headers"]["sign"] == "AQID"
    assert len(signer.sign_calls) == 1
    assert signer.sign_calls[0][1] == b"expanse/messenger/serialization/sign"


def test_decode_verifies_the_signature_and_delegates_to_the_inner_serializer(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=True)
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    decoded = serializer.decode(encoded)

    message = decoded.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"

    assert len(signer.verify_calls) == 1
    _, signature, purpose = signer.verify_calls[0]
    assert signature == b"\x01\x02\x03"
    assert purpose == b"expanse/messenger/serialization/sign"


def test_decode_raises_when_the_signature_header_is_missing(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner()
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = _make_encoded_envelope(inner_serializer)

    with pytest.raises(MessageDecodingFailedError, match="Missing signature"):
        serializer.decode(encoded)

    assert signer.verify_calls == []


def test_decode_raises_when_the_signature_is_invalid(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=False)
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_decode_raises_when_the_body_has_been_tampered_with(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=True)
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    tampered = b'{"foo":"tampered"}'
    encoded["body"] = tampered

    signer.verifies = False

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_round_trip_with_a_real_signer(inner_serializer: InnerSerializer) -> None:
    """
    End-to-end test with the real HMAC-based signer, exercising the actual
    hex encoding/decoding of the signature header.
    """
    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(inner_serializer, signer)

    envelope = Envelope.wrap(Foo(foo="bar"))
    encoded = serializer.encode(envelope)

    assert isinstance(encoded["headers"]["sign"], str)

    decoded = serializer.decode(encoded)
    message = decoded.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"


def test_round_trip_with_a_real_signer_rejects_a_tampered_signature(
    inner_serializer: InnerSerializer,
) -> None:
    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["sign"] = "00" * (len(encoded["headers"]["sign"]) // 2)

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_round_trip_with_a_real_signer_rejects_tampered_headers(
    inner_serializer: InnerSerializer,
) -> None:
    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["stamps"] = [b"tampered"]

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_decode_raises_when_the_signature_header_is_not_valid_hex(
    inner_serializer: InnerSerializer,
) -> None:
    signer = FakeSigner()
    serializer = SigningSerializer(inner_serializer, signer)

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["sign"] = "not-hex"

    with pytest.raises(MessageDecodingFailedError, match="Malformed signature"):
        serializer.decode(encoded)

    assert signer.verify_calls == []
