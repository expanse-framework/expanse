from pathlib import Path
from typing import TYPE_CHECKING

from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal


class CacheServiceProvider(ServiceProvider):
    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
