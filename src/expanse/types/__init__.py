from __future__ import annotations

from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import MutableMapping
from types import TracebackType
from typing import Any
from typing import Protocol


Environ = MutableMapping[str, Any]
ExcInfo = tuple[type[BaseException], BaseException, TracebackType | None]


class StartResponse(Protocol):
    def __call__(
        self,
        status: str,
        response_headers: tuple[str, str],
        exc_info: ExcInfo | None = None,
    ) -> None: ...


WSGIApp = Callable[[Environ, StartResponse], Iterable[bytes]]
