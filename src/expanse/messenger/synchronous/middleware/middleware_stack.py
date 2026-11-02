from expanse.messenger.synchronous.middleware.middleware import Middleware
from expanse.support.middleware.middleware_stack import (
    MiddlewareStack as BaseMiddlewareStack,
)


class MiddlewareStack(BaseMiddlewareStack[Middleware]):
    """
    Middleware stack for the synchronous message bus.
    """

    def get_default_middleware(self) -> list[type[Middleware]]:
        from expanse.messenger.synchronous.middleware.ensure_unique import EnsureUnique
        from expanse.messenger.synchronous.middleware.handle_encryption import (
            HandleEncryption,
        )
        from expanse.messenger.synchronous.middleware.propagate_context import (
            PropagateContext,
        )

        return [
            EnsureUnique,
            PropagateContext,
            HandleEncryption,
        ]
