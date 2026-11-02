from collections.abc import Callable

from expanse.logging.context import Context
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.context import ContextStamp


class PropagateContext:
    """
    Middleware that adds the context information to the envelope upon dispatch.
    """

    def __init__(self, context: Context) -> None:
        self._context: Context = context

    def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Envelope]
    ) -> Envelope:
        return next_call(envelope.with_stamps(ContextStamp({**self._context})))
