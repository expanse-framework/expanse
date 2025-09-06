from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Protocol
from typing import overload


class SyncJobType(Protocol):
    def handle(self, *args: Any, kwargs: Any) -> None: ...


class AsyncJobType(Protocol):
    @overload
    async def handle(self) -> None: ...

    @overload
    async def handle(self, *args: Any) -> None: ...

    @overload
    async def handle(self, **kwargs: Any) -> None: ...

    @overload
    async def handle(self, *args: Any, **kwargs: Any) -> None: ...

    async def handle(self, *args: Any, kwargs: Any) -> None: ...


type JobType = (
    SyncJobType | AsyncJobType | Callable[..., None] | Callable[..., Awaitable[None]]
)
