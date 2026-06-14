from expanse.contracts.cache.synchronous.cache import Cache
from expanse.http.request import Request
from expanse.session.synchronous.stores.store import Store


class CacheStore(Store):
    def __init__(self, cache: Cache, lifetime: int) -> None:
        self._cache: Cache = cache
        self._lifetime: int = lifetime

    def read(self, session_id: str) -> str:
        """
        Read the session data from the cache.

        :param session_id: The session ID.
        :return: The session data.
        """
        return self._cache.get(session_id) or ""

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        """
        Write the session data to the cache.

        :param session_id: The session ID.
        :param data: The session data.
        :param request: The HTTP request (optional).
        """
        self._cache.set(session_id, data, self._lifetime * 60)

    def delete(self, session_id: str) -> None:
        """
        Delete the session data from the cache.

        :param session_id: The session ID.
        """
        self._cache.delete(session_id)

    def clear(self) -> int:
        """
        Clear all session data from the cache.

        :return: The number of sessions cleared.
        """
        return 0
