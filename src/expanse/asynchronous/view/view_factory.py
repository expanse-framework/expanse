from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

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

    async def make(self, view: str, data: dict[str, Any] | None = None) -> Response:
        template = self._env.get_template(view)

        content = await template.render_async(data or {})

        return Response(content=content, media_type="text/html")
