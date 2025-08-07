from collections.abc import Mapping
from typing import Any
from typing import Self

from expanse.view.view import View
from expanse.view.view_manager import ViewManager


class ViewFactory:
    def __init__(self, manager: ViewManager) -> None:
        self._manager: ViewManager = manager
        self._locals: dict[str, Any] = {}

    def make(self, view: str, data: Mapping[str, Any] | None = None) -> View:
        return View(view, data)

    async def render(self, view: View) -> str:
        template = self._manager.template(view.identifier)

        content: str = await template.render_async({**view.data, **self._locals})

        return content

    def register_local(self, **locals: Any) -> Self:
        self._locals.update(locals)

        return self

    def exists(self, view: str) -> bool:
        return self._manager.exists(view)
