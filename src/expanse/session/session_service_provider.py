from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.session.middleware.load_session import LoadSession
from expanse.session.session_manager import SessionManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.gateway import Gateway


class SessionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_session_manager()

        self._container.singleton(LoadSession, self._create_load_session)

    async def boot(self) -> None:
        from expanse.core.console.gateway import Gateway

        await self._container.on_resolved(Gateway, self._register_command_path)

    async def _register_session_manager(self) -> None:
        self._container.singleton("session:manager", SessionManager)

    async def _create_load_session(self, container: Container) -> LoadSession:
        session_manager: SessionManager = await container.get("session:manager")

        return LoadSession(session_manager)

    async def _register_command_path(self, gateway: "Gateway") -> None:
        await gateway.load_path(Path(__file__).parent.joinpath("console/commands"))
