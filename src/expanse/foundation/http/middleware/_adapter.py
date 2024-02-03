from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.datastructures import Headers

from expanse.http.request import Request
from expanse.http.response import Response
from expanse.support._compat import aclosing


if TYPE_CHECKING:
    from starlette.types import ASGIApp
    from starlette.types import Message
    from starlette.types import Receive
    from starlette.types import Scope
    from starlette.types import Send

    from expanse.container.container import Container
    from expanse.foundation.http.middleware.base import Middleware


class AdapterMiddleware:
    def __init__(
        self, app: ASGIApp, middleware: type[Middleware], container: Container
    ) -> None:
        self.app: ASGIApp = app
        self._container: Container = container
        self._middleware_class = middleware
        self._middleware: Middleware | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        if self._middleware is None:
            self._middleware = await self._container.make(self._middleware_class)

        async with aclosing(self._middleware.handle(request)) as flow:
            # Kick the flow until the first `yield`.
            # Might respond early before we call into the app.
            maybe_early_response = await flow.__anext__()

            if maybe_early_response is not None:
                try:
                    await flow.__anext__()
                except StopAsyncIteration:
                    pass
                else:
                    raise RuntimeError("dispatch() should yield exactly once")

                await maybe_early_response(scope, receive, send)
                return

            response_started = False

            async def wrapped_send(message: Message) -> None:
                nonlocal response_started

                if message["type"] == "http.response.start":
                    response_started = True

                    headers = Headers(raw=message["headers"])
                    response = Response(
                        status_code=message["status"],
                        media_type=headers.get("content-type"),
                    )
                    response.raw_headers = headers.raw

                    try:
                        await flow.asend(response)
                    except StopAsyncIteration:
                        pass
                    else:
                        raise RuntimeError("dispatch() should yield exactly once")

                    message["headers"] = response.raw_headers

                await send(message)

            try:
                await self.app(scope, receive, wrapped_send)
            except Exception as exc:
                if response_started:
                    raise

                try:
                    response = await flow.athrow(exc)
                except StopAsyncIteration:
                    response = None
                except Exception:
                    # Exception was not handled, or they raised another one.
                    raise

                if response is None:
                    raise RuntimeError(
                        f"dispatch() handled exception {exc!r}, "
                        "but no response was returned"
                    )

                await response(scope, receive, send)

                return
