from typing import TYPE_CHECKING
from typing import cast
from typing import override

from expanse.cache.asynchronous.locks.lock import Lock
from expanse.redis.asynchronous.connections.connection import Connection


if TYPE_CHECKING:
    from redis.commands.core import AsyncScript


_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

_REFRESH_SCRIPT = """
if redis.call("get", KEYS[1]) ~= ARGV[1] then
    return 1
elseif redis.call("ttl", KEYS[1]) < 0 then
    return 2
else
    redis.call("expire", KEYS[1], ARGV[2])
    return 0
end
"""


class RedisLock(Lock):
    def __init__(
        self,
        connection: Connection,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> None:
        super().__init__(f"lock:{name}", ttl, owner, refresh=refresh)

        self._connection: Connection = connection
        self._release_script: AsyncScript = self._connection.register_script(  # type: ignore[misc]
            _RELEASE_SCRIPT
        )
        self._refresh_script: AsyncScript = self._connection.register_script(  # type: ignore[misc]
            _REFRESH_SCRIPT
        )

    @override
    async def get_current_owner(self) -> str | None:
        return cast("str | None", await self._connection.get(self._name))

    @override
    async def _do_acquire(self) -> bool:
        result = await self._connection.set(
            self._name,
            self._owner,
            ex=self._ttl if self._ttl is not None else None,
            nx=True,
        )
        if result is None:
            return False

        return cast("bool", result)

    @override
    async def _do_release(self, force: bool = False) -> bool:
        if force:
            return cast("bool", await self._connection.delete(self._name) > 0)

        return (
            cast(
                "int", await self._release_script(keys=[self._name], args=[self._owner])
            )
            > 0
        )

    @override
    async def refresh(self, ttl: int | None = None) -> bool:
        if ttl is None:
            ttl = self._ttl

        assert ttl is not None, "TTL must be provided to refresh the lock."

        result: int = cast(
            "int",
            await self._refresh_script(keys=[self._name], args=[self._owner, ttl]),
        )

        return not result > 0
