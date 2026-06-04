from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast
from typing import override

from expanse.cache.synchronous.locks.lock import Lock


if TYPE_CHECKING:
    from redis.commands.core import Script

    from expanse.redis.synchronous.connections.connection import Connection


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
        self._release_script: Script = self._connection.register_script(_RELEASE_SCRIPT)
        self._refresh_script: Script = self._connection.register_script(_REFRESH_SCRIPT)

    @override
    def get_current_owner(self) -> str | None:
        return cast("str | None", self._connection.get(self._name))

    @override
    def _do_acquire(self) -> bool:
        return cast(
            "bool",
            self._connection.set(
                self._name,
                self._owner,
                ex=self._ttl if self._ttl is not None else None,
                nx=True,
            ),
        )

    @override
    def _do_release(self, force: bool = False) -> bool:
        if force:
            return cast("int", self._connection.delete(self._name)) > 0

        return (
            cast("int", self._release_script(keys=[self._name], args=[self._owner])) > 0
        )

    @override
    def refresh(self, ttl: int | None = None) -> bool:
        if ttl is None:
            ttl = self._ttl

        assert ttl is not None, "TTL must be provided to refresh the lock."

        result: int = cast(
            "int",
            self._refresh_script(keys=[self._name], args=[self._owner, ttl]),
        )

        return not result > 0
