from typing import Any

import msgspec

from expanse.contracts.encryption.signer import Signer
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.types.messenger import EncodedEnvelope
from expanse.types.serialization import Encoded


class SigningSerializer(SerializerContract):
    _PURPOSE: bytes = b"expanse/messenger/serialization/sign"

    def __init__(
        self,
        inner_serializer: SerializerContract,
        signer: Signer,
    ) -> None:
        self._inner_serializer: SerializerContract = inner_serializer
        self._signer: Signer = signer

    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        encoded = self._inner_serializer.encode(envelope)

        encoded["headers"]["sign"] = self._signer.sign(
            self._signing_payload(encoded["body"], encoded["headers"]),
            purpose=self._PURPOSE,
        ).hex()

        return encoded

    def decode(self, encoded_envelope: EncodedEnvelope) -> Envelope:
        headers = encoded_envelope["headers"]
        signature: str | None = headers.get("sign")

        if signature is None:
            raise MessageDecodingFailedError("Missing signature in headers")

        try:
            raw_signature = bytes.fromhex(signature)
            unsigned_headers = {k: v for k, v in headers.items() if k != "sign"}
            payload = self._signing_payload(encoded_envelope["body"], unsigned_headers)
        except (TypeError, ValueError, msgspec.EncodeError) as e:
            raise MessageDecodingFailedError("Malformed signature in headers") from e

        if not self._signer.verify(payload, raw_signature, purpose=self._PURPOSE):
            raise MessageDecodingFailedError("Invalid signature")

        return self._inner_serializer.decode(encoded_envelope)

    def _signing_payload(self, body: Encoded, headers: dict[str, Any]) -> bytes:
        return msgspec.json.encode({"body": body, "headers": headers})
