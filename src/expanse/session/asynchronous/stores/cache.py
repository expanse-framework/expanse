from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.http.request import Request
from expanse.session.asynchronous.stores.store import AsyncStore


class AsyncCacheStore(AsyncStore):
    def __init__(self, cache: Cache, lifetime: int) -> None:
        self._cache: Cache = cache
        self._lifetime: int = lifetime

    async def read(self, session_id: str) -> str:
        """
        Read the session data from the cache.

        :param session_id: The session ID.
        :return: The session data.
        """
        return await self._cache.get(session_id) or ""

    async def write(
        self, session_id: str, data: str, request: Request | None = None
    ) -> None:
        """
        Write the session data to the cache.

        :param session_id: The session ID.
        :param data: The session data.
        :param request: The HTTP request (optional).
        """
        await self._cache.set(session_id, data, self._lifetime * 60)

    async def delete(self, session_id: str) -> None:
        """
        Delete the session data from the cache.

        :param session_id: The session ID.
        """
        await self._cache.delete(session_id)

    async def clear(self) -> int:
        """
        Clear all session data from the cache.

        :return: The number of sessions cleared.
        """
        return 0
