from expanse.messenger.envelope import Envelope
from expanse.support.middleware.middleware import Middleware
from expanse.support.middleware.middleware_stack import (
    MiddlewareStack as BaseMiddlewareStack,
)


class MiddlewareStack(BaseMiddlewareStack[Middleware[Envelope, Envelope]]):
    """
    Middleware stack for the messenger.
    """

    def get_default_middleware(
        self,
    ) -> list[type[Middleware[Envelope, Envelope]]]:
        from expanse.messenger.middleware.ensure_unique import EnsureUnique
        from expanse.messenger.middleware.handle_encryption import HandleEncryption
        from expanse.messenger.middleware.handle_failed_decoding import (
            HandleFailedDecoding,
        )
        from expanse.messenger.middleware.propagate_context import PropagateContext
        from expanse.messenger.middleware.relay_messages import RelayMessages

        # RelayMessages must stay last: the stack is executed in reverse
        # upon reception, so that outboxed messages are relayed untouched.
        return [
            HandleFailedDecoding,
            EnsureUnique,
            PropagateContext,
            HandleEncryption,
            RelayMessages,
        ]
