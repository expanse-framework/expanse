from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.http.request import Request


class AsyncStore(ABC):
    @abstractmethod
    async def read(self, session_id: str) -> str: ...

    @abstractmethod
    async def write(
        self, session_id: str, data: str, request: Request | None = None
    ) -> None: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def clear(self) -> int: ...
