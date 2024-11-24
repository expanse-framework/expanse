import pendulum

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
        session.set("ip_address", request.client.host)

        request.set_session(session)
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
        response.set_cookie(
            session.get_name(),
            session.get_id(),
            expires=await self._compute_expiration(),
            path=config["path"],
            domain=config["domain"],
            secure=config["secure"],
            httponly=config["http_only"],
            samesite=config["same_site"],
        )

    async def _compute_expiration(self) -> int:
        now = pendulum.now("UTC")

        return now.add(minutes=self._manager.get_config()["lifetime"])

    def _is_session_configured(self) -> bool:
        config = self._manager.get_config()

        return "store" in config and config["store"] is not None
