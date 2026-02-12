from collections.abc import Callable
from typing import Any


def async_safe(safe: bool = True) -> Callable[..., Any]:
    """
    Decorator to mark a function as safe/unsafe to run directly in an async context.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "is_async_safe", safe)  # noqa: B010

        return func

    return decorator
