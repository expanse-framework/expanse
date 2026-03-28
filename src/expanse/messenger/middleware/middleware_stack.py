from expanse.messenger.envelope import Envelope
from expanse.support.middleware.middleware import Middleware
from expanse.support.middleware.middleware_stack import (
    MiddlewareStack as BaseMiddlewareStack,
)


class MiddlewareStack(BaseMiddlewareStack[Envelope, Envelope]):
    """
    Middleware stack for the messenger.
    """

    def get_default_middleware(self) -> list[type[Middleware[Envelope, Envelope]]]:
        from expanse.messenger.middleware.handle_encryption import HandleEncryption

        return [HandleEncryption]
