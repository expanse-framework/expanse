from collections.abc import Callable
from typing import Any

from expanse.http.request import Request


class ArgumentBinder:
    __slots__ = ("is_async", "name", "resolve")

    def __init__(
        self, name: str, is_async: bool, resolve: Callable[[Request], Any]
    ) -> None:
        self.name: str = name
        self.is_async: bool = is_async
        self.resolve: Callable[[Request], Any] = resolve
