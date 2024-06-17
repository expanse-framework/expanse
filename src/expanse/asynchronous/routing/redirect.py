import textwrap

from typing import Any

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router


class Redirect:
    def __init__(self, router: Router, request: Request) -> None:
        self._router: Router = router
        self._request: Request = request

    async def to(
        self, url: str, status: int = 302, headers: dict[str, Any] | None = None
    ) -> Response:
        return self._create_response(url, status, headers)

    async def to_route(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        status: int = 302,
        headers: dict[str, Any] | None = None,
    ) -> Response:
        return self._create_response(
            await self._router.route(name, parameters=parameters),
            status=status,
            headers=headers,
        )

    def _create_response(
        self, url: str, status: int = 302, headers: dict[str, Any] | None = None
    ) -> Response:
        content = textwrap.dedent(
            """<!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="UTF-8" />
                    <meta http-equiv="refresh" content="0;url=\'%1$s\'" />

                    <title>Redirecting to {url}</title>
                </head>
                <body>
                    Redirecting to <a href="{url}">{url}</a>.
                </body>
            </html>"""
        ).format(
            url=url.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        response = Response(
            content, status_code=status, headers=headers, content_type="text/html"
        )
        response.headers["Location"] = url

        return response
