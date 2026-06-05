from collections.abc import Awaitable
from collections.abc import Callable

from expanse.logging.context import Context
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.context import ContextStamp
from expanse.messenger.stamps.received import ReceivedStamp


class PopulateContext:
    """
    Middleware that adds the context information to the envelope upon dispatch and hydrate
    the context upon reception.
    """

    def __init__(self, context: Context) -> None:
        self._context: Context = context

    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope:
        if envelope.has_stamp(ReceivedStamp):
            context_stamp = envelope.stamp(ContextStamp)
            if context_stamp:
                self._context.update(context_stamp.context)

            return await next_call(envelope)

        return await next_call(envelope.with_stamps(ContextStamp({**self._context})))
