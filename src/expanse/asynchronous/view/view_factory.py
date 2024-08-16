from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import Self
from typing import overload

from jinja2.environment import Environment
from jinja2.loaders import FunctionLoader

from expanse.asynchronous.http.response import Response
from expanse.asynchronous.view.view import View


if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from expanse.asynchronous.view.view_finder import ViewFinder


class ViewFactory:
    def __init__(self, finder: ViewFinder, debug: bool = False) -> None:
        self._finder: ViewFinder = finder

        self._env = Environment(
            enable_async=True, loader=FunctionLoader(finder.find), auto_reload=debug
        )

    async def make(
        self,
        view: str,
        data: MutableMapping[str, Any] | None = None,
        status_code: int = 200,
        headers: MutableMapping[str, Any] | None = None,
    ) -> View:
        return View(view, data, status_code=status_code, headers=headers)

    @overload
    async def render(self, view: View, raw: Literal[False] = False) -> Response: ...

    @overload
    async def render(self, view: View, raw: Literal[True] = True) -> str: ...

    async def render(self, view: View, raw: bool = False) -> Response | str:
        template = self._env.get_template(view.identifier)

        content = await template.render_async(view.data)

        if raw:
            return content

        return Response(
            content=content,
            content_type="text/html",
            status_code=view.status_code,
            headers=view.headers,
        )

    def exists(self, view: str) -> bool:
        return self._finder.find(view) is not None

    def register_global(self, **globals: Any) -> Self:
        self._env.globals.update(globals)

        return self
