from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import Self
from typing import overload

from jinja2.environment import Environment
from jinja2.loaders import FunctionLoader

from expanse.http.response import Response
from expanse.view.view import View


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import MutableMapping

    from expanse.view.view_finder import ViewFinder


class ViewFactory:
    def __init__(self, finder: ViewFinder, debug: bool = False) -> None:
        self._finder: ViewFinder = finder

        self._env = Environment(
            loader=FunctionLoader(finder.find),
            cache_size=0 if debug else 400,
            auto_reload=debug,
        )

    def make(
        self,
        view: str,
        data: Mapping[str, Any] | None = None,
        status_code: int = 200,
        headers: MutableMapping[str, Any] | None = None,
    ) -> View:
        return View(view, data, status_code=status_code, headers=headers)

    @overload
    def render(self, view: View, raw: Literal[False] = False) -> Response: ...

    @overload
    def render(self, view: View, raw: Literal[True] = True) -> str: ...

    def render(self, view: View, raw: bool = False) -> Response | str:
        template = self._env.get_template(view.identifier)

        content = template.render(view.data)

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
