from expanse.http.request import Request
from expanse.session.asynchronous.stores.store import AsyncStore


class AsyncNullStore(AsyncStore):
    async def read(self, session_id: str) -> str:
        return ""

    async def write(
        self, session_id: str, data: str, request: Request | None = None
    ) -> None:
        pass

    async def delete(self, session_id: str) -> None:
        pass

    async def clear(self) -> int:
        return 0
