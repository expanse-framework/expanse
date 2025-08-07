from pathlib import Path
from typing import TYPE_CHECKING

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.session.middleware.load_session import LoadSession
from expanse.session.session_manager import SessionManager
from expanse.support.service_provider import ServiceProvider


if TYPE_CHECKING:
    from expanse.core.console.portal import Portal
    from expanse.exceptions.handler import ExceptionHandler
    from expanse.view.view_factory import ViewFactory


class SessionServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.exceptions.handler import ExceptionHandler

        await self._register_session_manager()

        self._container.singleton(LoadSession, self._create_load_session)

        await self._container.on_resolved(
            ExceptionHandler, self._configure_exception_handler
        )

    async def boot(self) -> None:
        from expanse.core.console.portal import Portal

        await self._container.on_resolved(Portal, self._register_command_path)

        await self._container.on_resolved("view", self._register_view_locals)
        await self._container.on_resolved(
            "view:async", self._register_async_view_locals
        )

    async def _register_session_manager(self) -> None:
        self._container.singleton("session:manager", SessionManager)

    async def _create_load_session(self, container: Container) -> LoadSession:
        session_manager: SessionManager = await container.get("session:manager")

        return LoadSession(session_manager)

    async def _register_command_path(self, portal: "Portal") -> None:
        await portal.load_path(Path(__file__).parent.joinpath("console/commands"))

    async def _configure_exception_handler(self, handler: "ExceptionHandler") -> None:
        from expanse.core.http.exceptions import HTTPException
        from expanse.session.exceptions import CSRFTokenMismatchError

        handler.dont_report(CSRFTokenMismatchError)
        handler.prepare_using(
            CSRFTokenMismatchError, lambda e: HTTPException(419, str(e))
        )

    async def _register_view_locals(
        self, view: "ViewFactory", request: Request
    ) -> None:
        def csrf_token() -> str | None:
            if not request.session:
                raise RuntimeError("Session is not loaded")

            return request.session.csrf_token

        view.register_local(csrf_token=csrf_token)

    async def _register_async_view_locals(
        self, view: "ViewFactory", request: Request
    ) -> None:
        def csrf_token() -> str | None:
            if not request.session:
                raise RuntimeError("Session is not loaded")

            return request.session.csrf_token

        view.register_local(csrf_token=csrf_token)
