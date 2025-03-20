import time

from math import ceil

from expanse.http.request import Request
from expanse.http.response import Response
from expanse.session.session import HTTPSession
from expanse.session.session_manager import SessionManager
from expanse.types.http.middleware import RequestHandler


class LoadSession:
    def __init__(self, manager: SessionManager) -> None:
        self._manager = manager

    async def handle(self, request: Request, next: RequestHandler) -> Response:
        if not self._is_session_configured():
            return await next(request)

        session = await self._get_session(request)
        request.set_session(await session.async_load())
        session.set_request(request)

        response = await next(request)

        await self._set_cookie(response, session)

        await session.async_save()

        return response

    async def _get_session(self, request: Request) -> HTTPSession:
        session = await self._manager.session()

        session.set_id(request.cookies.get(session.get_name()))

        return session

    async def _set_cookie(self, response: Response, session: HTTPSession) -> None:
        config = self._manager.get_config()
        response.with_cookie(
            session.get_name(),
            session.get_id(),
            expires=self._get_cookie_expiration_date(),
            path=config["path"],
            domain=config["domain"],
            secure=config["secure"],
            http_only=config["http_only"],
            same_site=config["same_site"],
        )

    def _is_session_configured(self) -> bool:
        config = self._manager.get_config()

        return "store" in config and config["store"] is not None

    def _get_cookie_expiration_date(self) -> int:
        if self._manager.get_config()["clear_with_browser"]:
            return 0

        return ceil(time.time() + self._manager.get_config()["lifetime"] * 60)
