from typing import NoReturn


def simple_exception() -> NoReturn:
    raise ValueError("Simple Exception")


def nested_exception() -> NoReturn:
    try:
        simple_exception()
    except ValueError:
        raise RuntimeError("Nested Exception")


def recursive_exception() -> None:
    def inner() -> None:
        outer()

    def outer() -> None:
        inner()

    inner()
