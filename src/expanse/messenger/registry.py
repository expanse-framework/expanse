from collections import defaultdict
from typing import get_type_hints

from expanse.messenger.exceptions import InvalidHandlerError
from expanse.types.messenger import Message
from expanse.types.messenger import MessageHandler
from expanse.types.messenger import MessageT


class Registry:
    def __init__(self):
        self._handlers: dict[type[Message], list[MessageHandler[Message]]] = (
            defaultdict(list)
        )

    def register(
        self, message_type: type[MessageT], handler: MessageHandler[MessageT]
    ) -> None:
        self._handlers[message_type].append(handler)

    def register_handler(self, handler: MessageHandler[Message]) -> None:
        hints = get_type_hints(handler)
        message_type: type[Message] | None
        if "message" not in hints:
            # If no `message` parameter is found ,we fall back to looking for the first parameter annotated with a message type.

            message_params = [
                param for param, hint in hints.items() if hint is not None
            ]
            message_type = None if not message_params else hints[message_params[0]]
        else:
            message_type = hints.get("message")

        if message_type is None:
            raise InvalidHandlerError(
                f"Handler {handler} must have a 'message' parameter annotated with the message type."
            )

        self.register(message_type, handler)

    def get_handlers(
        self, message_type: type[MessageT]
    ) -> list[MessageHandler[MessageT]]:
        return self._handlers.get(message_type, [])
