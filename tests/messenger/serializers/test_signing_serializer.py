from dataclasses import dataclass
from typing import Any

import pytest

from expanse.contracts.encryption.signer import Signer as SignerContract
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.signer import Signer
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.serializers.signing_serializer import SigningSerializer
from expanse.messenger.serializers.strict_serializer import (
    StrictSerializer as InnerSerializer,
)
from expanse.messenger.trusted_collection import TrustedCollection
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


def _make_encoded_envelope() -> EncodedEnvelope:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    inner = InnerSerializer(trusted_collection=trusted_collection)

    return inner.encode(Envelope.wrap(Foo(foo="bar")))


def test_encode_adds_a_hex_encoded_signature_header() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    signer = FakeSigner(signature=b"\x01\x02\x03")
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))

    assert encoded["headers"]["sign"] == "010203"
    assert len(signer.sign_calls) == 1
    assert signer.sign_calls[0][1] == b"expanse/messenger/serialization/sign"


def test_decode_verifies_the_signature_and_delegates_to_the_inner_serializer() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=True)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    decoded = serializer.decode(encoded)

    message = decoded.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"

    assert len(signer.verify_calls) == 1
    _, signature, purpose = signer.verify_calls[0]
    assert signature == b"\x01\x02\x03"
    assert purpose == b"expanse/messenger/serialization/sign"


def test_decode_raises_when_the_signature_header_is_missing() -> None:
    signer = FakeSigner()
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=TrustedCollection()), signer
    )

    encoded = _make_encoded_envelope()

    with pytest.raises(MessageDecodingFailedError, match="Missing signature"):
        serializer.decode(encoded)

    assert signer.verify_calls == []


def test_decode_raises_when_the_signature_is_invalid() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=False)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_decode_raises_when_the_body_has_been_tampered_with() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    signer = FakeSigner(signature=b"\x01\x02\x03", verifies=True)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    tampered: dict[str, Any] = dict(encoded["body"])
    tampered["d"] = '{"foo":"tampered"}'
    encoded["body"] = tampered  # type: ignore[typeddict-item]

    signer.verifies = False

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_round_trip_with_a_real_signer() -> None:
    """
    End-to-end test with the real HMAC-based signer, exercising the actual
    hex encoding/decoding of the signature header.
    """
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    envelope = Envelope.wrap(Foo(foo="bar"))
    encoded = serializer.encode(envelope)

    assert isinstance(encoded["headers"]["sign"], str)

    decoded = serializer.decode(encoded)
    message = decoded.open()
    assert isinstance(message, Foo)
    assert message.foo == "bar"


def test_round_trip_with_a_real_signer_rejects_a_tampered_signature() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["sign"] = "00" * (len(encoded["headers"]["sign"]) // 2)

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_round_trip_with_a_real_signer_rejects_tampered_headers() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    key_chain = KeyChain([Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")])
    signer = Signer(key_chain)
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["stamps"] = ["tampered"]

    with pytest.raises(MessageDecodingFailedError, match="Invalid signature"):
        serializer.decode(encoded)


def test_decode_raises_when_the_signature_header_is_not_valid_hex() -> None:
    trusted_collection = TrustedCollection()
    trusted_collection.trust(Foo)

    signer = FakeSigner()
    serializer = SigningSerializer(
        InnerSerializer(trusted_collection=trusted_collection), signer
    )

    encoded = serializer.encode(Envelope.wrap(Foo(foo="bar")))
    encoded["headers"]["sign"] = "not-hex"

    with pytest.raises(MessageDecodingFailedError, match="Malformed signature"):
        serializer.decode(encoded)

    assert signer.verify_calls == []
