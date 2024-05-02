from typing import TYPE_CHECKING

from expanse.common.configuration.config import Config
from expanse.static.static import Static
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import ViewFactory


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.routing.router import Router


class StaticServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._app.singleton(Static, self._register_static)

    def boot(self) -> None:
        self._app.on_resolved("router", self._add_static_route)
        self._app.on_resolved("view", self._register_view_globals)

    def _register_static(self, config: Config) -> Static:
        paths: list[Path] = [
            self._app.resolve_placeholder_path(p)
            for p in config.get("static.paths", [])
        ]

        return Static(
            paths, prefix=config.get("static.prefix"), url=config.get("static.url")
        )

    def _add_static_route(self, router: "Router") -> None:
        if self._app.config.get("app.debug", False):
            prefix: str = self._app.config["static.prefix"].rstrip("/")

            router.get(
                f"{prefix}/{{path:path}}", self._app.make(Static).get, name="static"
            )

    def _register_view_globals(self, view: ViewFactory) -> None:
        view.register_global(static=self._app.make(Static).url)
