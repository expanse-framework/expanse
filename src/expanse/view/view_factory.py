from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from jinja2.environment import Environment
from jinja2.loaders import FunctionLoader

from expanse.http.response import Response


if TYPE_CHECKING:
    from expanse.view.view_finder import ViewFinder


class ViewFactory:
    def __init__(self, finder: ViewFinder, debug: bool = False) -> None:
        self._finder: ViewFinder = finder

        self._env = Environment(
            loader=FunctionLoader(finder.find),
            cache_size=0 if debug else 400,
            auto_reload=debug,
        )

    def make(self, view: str, data: dict[str, Any] | None = None) -> Response:
        template = self._env.get_template(view)

        content = template.render(data or {})

        return Response(content=content, media_type="text/html")

    def register_global(self, **globals: Any) -> Self:
        self._env.globals.update(globals)

        return self
