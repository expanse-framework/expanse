from typing import TYPE_CHECKING
from typing import Any

from jinja2 import Environment
from jinja2 import FunctionLoader

from expanse.core.application import Application
from expanse.view.view_finder import ViewFinder


if TYPE_CHECKING:
    from collections.abc import MutableMapping


class ViewManager:
    def __init__(self, app: Application, finder: ViewFinder) -> None:
        self._finder: ViewFinder = finder

        self._env = Environment(
            enable_async=True,
            loader=FunctionLoader(self._finder.find),
            auto_reload=app.config.get("app.debug", False),
        )

        self._scoped: MutableMapping[str, Any] = {}

    def template(self, name: str) -> Any:
        return self._env.get_template(name)

    def exists(self, view: str) -> bool:
        return self._finder.find(view) is not None

    def register_global(self, **globals: Any) -> None:
        self._env.globals.update(globals)
