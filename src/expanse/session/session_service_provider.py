from expanse.container.container import Container
from expanse.session.middleware.load_session import LoadSession
from expanse.session.session_manager import SessionManager
from expanse.support.service_provider import ServiceProvider


class SessionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_session_manager()

        self._container.singleton(LoadSession, self._create_start_session)

    async def _register_session_manager(self) -> None:
        self._container.singleton("session:manager", SessionManager)

    async def _create_start_session(self, container: Container) -> LoadSession:
        session_manager: SessionManager = await container.get("session:manager")

        return LoadSession(session_manager)
