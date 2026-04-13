import importlib
import inspect

from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from typing import TypeVar
from typing import get_type_hints

from expanse.messenger.exceptions import InvalidHandlerError
from expanse.types.messenger import MessageHandler


if TYPE_CHECKING:
    from expanse.types import Message


T = TypeVar("T")


class HandlerDefinition(TypedDict):
    handler: MessageHandler[Any]
    message_type: type


def message_handler() -> Callable[[MessageHandler[T]], MessageHandler[T]]:
    """
    Decorator to mark a function as a message handler.

    :param func: The function to mark as a message handler.
    :return: The original function, marked as a message handler.
    """

    def decorator(handler: MessageHandler[T]) -> MessageHandler[T]:
        module = inspect.getmodule(handler)
        if module is None:
            module_name = handler.__module__

            module = importlib.import_module(module_name)

        if module is None:
            return handler

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

        if not hasattr(module, "__message_handlers__"):
            setattr(module, "__message_handlers__", {})  # noqa: B010

        module.__message_handlers__[handler.__name__] = HandlerDefinition(
            handler=handler,
            message_type=message_type,
        )

        return handler

    return decorator
