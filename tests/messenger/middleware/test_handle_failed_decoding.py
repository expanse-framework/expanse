from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import override

import pytest

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.middleware.handle_failed_decoding import HandleFailedDecoding
from expanse.messenger.stamps.received import ReceivedStamp


if TYPE_CHECKING:
    from expanse.types.messenger import EncodedEnvelope


@dataclass
class Message:
    value: str


@dataclass(frozen=True)
class DecodedStamp:
    name: str


ENCODED_ENVELOPE: EncodedEnvelope = {"body": b"payload", "headers": {}}


class FakeSerializer(SerializerContract):
    """
    A test double whose ``decode`` either returns a preconfigured envelope
    or raises a preconfigured exception. ``encode`` is not exercised here.
    """

    def __init__(
        self,
        decoded_envelope: Envelope | None = None,
        raise_on_decode: Exception | None = None,
    ) -> None:
        self.decoded_envelope: Envelope | None = decoded_envelope
        self.raise_on_decode: Exception | None = raise_on_decode
        self.decode_calls: list[EncodedEnvelope] = []

    @override
    def encode(self, envelope: Envelope) -> EncodedEnvelope:
        raise NotImplementedError

    @override
    def decode(self, encoded_envelope: EncodedEnvelope) -> Envelope:
        self.decode_calls.append(encoded_envelope)

        if self.raise_on_decode is not None:
            raise self.raise_on_decode

        assert self.decoded_envelope is not None
        return self.decoded_envelope


class Handler:
    def __init__(self) -> None:
        self.calls: list[Envelope] = []

    async def handle(self, envelope: Envelope) -> Envelope:
        self.calls.append(envelope)

        return envelope


async def test_calls_next_when_message_is_not_a_decoding_error() -> None:
    handler = Handler()
    serializer = FakeSerializer()
    middleware = HandleFailedDecoding(serializer)

    envelope = Envelope(Message("hello"))

    result = await middleware.handle(envelope, handler.handle)

    assert result is envelope
    assert handler.calls == [envelope]
    assert serializer.decode_calls == []


async def test_raises_runtime_error_when_envelope_has_no_received_stamp() -> None:
    handler = Handler()
    serializer = FakeSerializer()
    middleware = HandleFailedDecoding(serializer)

    error = MessageDecodingFailedError("boom", encoded_envelope=ENCODED_ENVELOPE)
    envelope = Envelope(error)

    with pytest.raises(RuntimeError, match="does not have a ReceivedStamp"):
        await middleware.handle(envelope, handler.handle)

    assert handler.calls == []
    assert serializer.decode_calls == []


async def test_calls_next_with_decoded_stamps_when_encoded_envelope_decodes_cleanly() -> (
    None
):
    handler = Handler()
    decoded_stamp = DecodedStamp("recovered")
    decoded_envelope = Envelope(Message("decoded"), stamps=[decoded_stamp])
    serializer = FakeSerializer(decoded_envelope=decoded_envelope)
    middleware = HandleFailedDecoding(serializer)

    error = MessageDecodingFailedError("boom", encoded_envelope=ENCODED_ENVELOPE)
    envelope = Envelope(error, stamps=[ReceivedStamp()])

    result = await middleware.handle(envelope, handler.handle)

    assert serializer.decode_calls == [ENCODED_ENVELOPE]
    assert len(handler.calls) == 1

    passed_envelope: Envelope = handler.calls[0]
    assert passed_envelope.open() == Message("decoded")
    assert passed_envelope.has_stamp(ReceivedStamp)
    assert passed_envelope.stamps(DecodedStamp) == [decoded_stamp]
    assert result is passed_envelope


async def test_raises_the_original_error_when_the_decoded_envelope_still_wraps_a_decoding_error() -> (
    None
):
    handler = Handler()
    inner_error = MessageDecodingFailedError("inner", encoded_envelope=ENCODED_ENVELOPE)
    decoded_envelope = Envelope(inner_error)
    serializer = FakeSerializer(decoded_envelope=decoded_envelope)
    middleware = HandleFailedDecoding(serializer)

    original_error = MessageDecodingFailedError(
        "outer", encoded_envelope=ENCODED_ENVELOPE
    )
    envelope = Envelope(original_error, stamps=[ReceivedStamp()])

    with pytest.raises(MessageDecodingFailedError) as excinfo:
        await middleware.handle(envelope, handler.handle)

    assert excinfo.value is original_error
    assert handler.calls == []


async def test_propagates_the_error_when_decoding_the_encoded_envelope_fails_again() -> (
    None
):
    handler = Handler()
    reraised = MessageDecodingFailedError(
        "still broken", encoded_envelope=ENCODED_ENVELOPE
    )
    serializer = FakeSerializer(raise_on_decode=reraised)
    middleware = HandleFailedDecoding(serializer)

    original_error = MessageDecodingFailedError(
        "boom", encoded_envelope=ENCODED_ENVELOPE
    )
    envelope = Envelope(original_error, stamps=[ReceivedStamp()])

    with pytest.raises(MessageDecodingFailedError) as excinfo:
        await middleware.handle(envelope, handler.handle)

    assert excinfo.value is reraised
    assert handler.calls == []
