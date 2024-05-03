from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from jinja2.environment import Environment
from jinja2.loaders import FunctionLoader

from expanse.asynchronous.http.response import Response


if TYPE_CHECKING:
    from expanse.view.view_finder import ViewFinder


class ViewFactory:
    def __init__(self, finder: ViewFinder, debug: bool = False) -> None:
        self._finder: ViewFinder = finder

        self._env = Environment(
            enable_async=True, loader=FunctionLoader(finder.find), auto_reload=debug
        )

    async def make(
        self,
        view: str,
        data: dict[str, Any] | None = None,
        status_code: int = 200,
        headers: dict[str, Any] | None = None,
    ) -> Response:
        template = self._env.get_template(view)

        content = await template.render_async(data or {})

        return Response(
            content=content,
            media_type="text/html",
            status_code=status_code,
            headers=headers,
        )

    def exists(self, view: str) -> bool:
        return self._finder.find(view) is not None

    def register_global(self, **globals: Any) -> Self:
        self._env.globals.update(globals)

        return self
