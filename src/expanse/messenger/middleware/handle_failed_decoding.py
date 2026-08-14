from collections.abc import Awaitable
from collections.abc import Callable

from expanse.contracts.messenger.serializer import Serializer
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.stamps.received import ReceivedStamp


class HandleFailedDecoding:
    """
    Middleware to handle failed decoding of messages.

    Upon receipt, if the message is a `MessageDecodingFailedError` the middleware tries to decode the associated encoded envelope.
    If it fails again, it raises the `MessageDecodingFailedError` exception. Otherwise, it passes the decoded envelope to the next middleware or handler.
    """

    def __init__(self, serializer: Serializer) -> None:
        self._serializer = serializer

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        message = envelope.open()

        if not isinstance(message, MessageDecodingFailedError):
            return await next_call(envelope)

        if not envelope.has_stamp(ReceivedStamp):
            # This should not happen in practive since decoding errors should only occur on received messages, but we check it just in case.
            raise RuntimeError(
                "Received a MessageDecodingFailedError for an envelope that does not have a ReceivedStamp."
            )

        decoded_envelope = self._serializer.decode(message.encoded_envelope)

        if isinstance(decoded_envelope.open(), MessageDecodingFailedError):
            raise message

        return await next_call(decoded_envelope.with_stamps(*envelope.stamps()))
