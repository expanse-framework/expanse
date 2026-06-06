from pathlib import Path
from typing import TYPE_CHECKING

from expanse.cache.asynchronous.cache_manager import CacheManager as AsyncCacheManager
from expanse.cache.synchronous.cache_manager import CacheManager as SyncCacheManager
from expanse.contracts.cache.asynchronous.cache import Cache as AsyncCache
from expanse.contracts.cache.synchronous.cache import Cache as SyncCache
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal


class CacheServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(SyncCacheManager)
        self._container.singleton(AsyncCacheManager)
        self._container.singleton(SyncCache, self._get_sync_cache)
        self._container.singleton(AsyncCache, self._get_async_cache)

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _get_sync_cache(
        self, manager: SyncCacheManager, name: str | None = None
    ) -> SyncCache:
        return await manager.cache(name)

    async def _get_async_cache(
        self, manager: AsyncCacheManager, name: str | None = None
    ) -> AsyncCache:
        return await manager.cache(name)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
