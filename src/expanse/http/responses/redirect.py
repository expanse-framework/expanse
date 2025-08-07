import textwrap

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Self

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.responses.response import Response


@dataclass(frozen=True, slots=True)
class RouteRediretion:
    name: str
    parameters: dict[str, Any]
    absolute: bool = False


class RedirectResponse(Response):
    """
    A response that represents a redirect to a named route or specific URL.
    """

    __slots__ = ("_route_redirection", "_url")

    def __init__(
        self, status_code: int = 302, *, headers: Mapping[str, str] | None = None
    ) -> None:
        super().__init__(
            content=None,
            status_code=status_code,
            headers=headers,
            content_type="text/html",
        )

        self._route_redirection: RouteRediretion | None = None
        self._url: str | None = None

    def to(self, url: str) -> Self:
        self._url = url

        return self

    def to_route(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> Self:
        self._route_redirection = RouteRediretion(
            name=name, parameters=parameters or {}, absolute=absolute
        )

        return self

    async def prepare(self, request: Request, container: Container) -> None:
        """
        Prepare the response before being sent to the client.

        This ensures that the redirect content and location are properly set up.
        """
        if self._url is None and self._route_redirection is None:
            raise RuntimeError("Either 'url' or 'route' must be set for redirection.")

        url: str
        if self._route_redirection is not None:
            from expanse.routing.url_generator import URLGenerator

            generator = await container.get(URLGenerator)
            url = generator.to_route(
                self._route_redirection.name,
                self._route_redirection.parameters,
                absolute=self._route_redirection.absolute,
            )
        elif self._url is not None:
            url = self._url
        else:
            raise RuntimeError("Either 'url' or 'route' must be set for redirection.")

        self._content = textwrap.dedent(
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

        self.headers["Location"] = url

        return await super().prepare(request, container)
