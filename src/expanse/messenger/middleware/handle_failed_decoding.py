from collections.abc import Awaitable
from collections.abc import Callable

from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.stamps.received import ReceivedStamp


class HandleFailedDecoding:
    """
    Middleware to handle failed decoding of messages.
    """

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        if not envelope.has_stamp(ReceivedStamp):
            return await next_call(envelope)

        message = envelope.open()

        if not isinstance(message, MessageDecodingFailedError):
            return await next_call(envelope)

        raise message
