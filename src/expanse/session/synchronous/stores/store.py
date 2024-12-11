from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.http.request import Request


class Store(ABC):
    @abstractmethod
    def read(self, session_id: str) -> str: ...

    @abstractmethod
    def write(
        self, session_id: str, data: str, request: Request | None = None
    ) -> None: ...

    @abstractmethod
    def delete(self, session_id: str) -> None: ...

    @abstractmethod
    def clear(self) -> int: ...
