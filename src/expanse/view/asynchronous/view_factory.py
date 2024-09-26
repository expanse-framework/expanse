from collections.abc import MutableMapping
from typing import Any
from typing import Literal
from typing import Self
from typing import overload

from expanse.http.response import Response
from expanse.view.view import View
from expanse.view.view_manager import ViewManager


class AsyncViewFactory:
    def __init__(self, manager: ViewManager) -> None:
        self._manager: ViewManager = manager
        self._locals: dict[str, Any] = {}

    def make(
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
        template = self._manager.template(view.identifier)

        content = await template.render_async({**view.data, **self._locals})

        if raw:
            return content

        return Response(
            content=content,
            content_type="text/html",
            status_code=view.status_code,
            headers=view.headers,
        )

    def register_local(self, **locals: Any) -> Self:
        self._locals.update(locals)

        return self

    def exists(self, view: str) -> bool:
        return self._manager.exists(view)
