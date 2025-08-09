from typing import Any
from typing import Protocol


class SyncJobType(Protocol):
    def handle(self, *args: Any, kwargs: Any) -> None: ...


class AsyncJobType(Protocol):
    async def handle(self, *args: Any, kwargs: Any) -> None: ...


type JobType = SyncJobType | AsyncJobType
