import textwrap

from typing import Any

from expanse.contracts.routing.router import Router
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.url_generator import URLGenerator


class Redirect:
    def __init__(
        self, router: Router, request: Request, generator: URLGenerator
    ) -> None:
        self._router: Router = router
        self._request: Request = request
        self._generator: URLGenerator = generator

    def to(
        self, url: str, status: int = 302, headers: dict[str, Any] | None = None
    ) -> Response:
        return self._create_response(url, status, headers)

    def to_route(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        status: int = 302,
        headers: dict[str, Any] | None = None,
    ) -> Response:
        return self._create_response(
            self._generator.to_route(name, parameters),
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
