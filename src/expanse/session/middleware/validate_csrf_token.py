import hmac
import time

from expanse.contracts.encryption.encryptor import Encryptor
from expanse.core.application import Application
from expanse.http.cookie import SameSite
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.session.exceptions import CSRFTokenMismatchError
from expanse.types.http.middleware import RequestHandler


class ValidateCSRFToken:
    add_xsrf_cookie: bool = True

    def __init__(self, app: Application, encryptor: Encryptor) -> None:
        self._app = app
        self._encryptor = encryptor

    async def handle(self, request: Request, next_: RequestHandler) -> Response:
        if request.method in {
            "GET",
            "HEAD",
            "OPTIONS",
            "TRACE",
        } or await self._has_valid_csrf_token(request):
            response = await next_(request)

            if self.add_xsrf_cookie:
                await self._add_xsrf_cookie(request, response)

            return response

        raise CSRFTokenMismatchError("CSRF token mismatch")

    async def _has_valid_csrf_token(self, request: Request) -> bool:
        token = await self._retrieve_csrf_token(request)
        if not request.session:
            return False

        session_token = request.session.csrf_token

        return (
            token is not None
            and session_token is not None
            and hmac.compare_digest(token, session_token)
        )

    async def _retrieve_csrf_token(self, request: Request) -> str | None:
        token = await request.input("_token", request.headers.get("X-CSRF-TOKEN"))

        if not token and (header := request.headers.get("X-XSRF-TOKEN")):
            try:
                token = self._encryptor.decrypt(header)
            except Exception:
                token = ""

        return token

    async def _add_xsrf_cookie(self, request: Request, response: Response) -> None:
        config = self._app.config["session"]

        assert request.session is not None

        if not response.cookies.get("XSRF-TOKEN"):
            response.with_cookie(
                "XSRF-TOKEN",
                request.session.csrf_token,
                expires=time.time() + config["lifetime"] * 60,
                path=config["path"],
                domain=config["domain"],
                secure=config["secure"],
                http_only=False,
                same_site=SameSite(config["same_site"]),
            )
