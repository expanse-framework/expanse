from pathlib import Path
from typing import TYPE_CHECKING

from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal as ConsolePortal


class JobsServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.jobs.asynchronous.job_dispatcher import (
            JobDispatcher as AsyncJobDispatcher,
        )
        from expanse.jobs.synchronous.job_dispatcher import (
            JobDispatcher as SyncJobDispatcher,
        )

        self._container.scoped(AsyncJobDispatcher)
        self._container.scoped(SyncJobDispatcher)

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal as ConsolePortal

        await self._container.on_resolved(
            ConsolePortal, self._register_console_commands
        )

    async def _register_console_commands(self, portal: "ConsolePortal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))
