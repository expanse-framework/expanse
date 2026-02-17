from collections.abc import Callable


def async_safe[**P, R](safe: bool = True) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to mark a function as safe/unsafe to run directly in an async context.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        setattr(func, "is_async_safe", safe)  # noqa: B010

        return func

    return decorator
