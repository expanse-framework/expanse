from typing import TYPE_CHECKING

from expanse.common.configuration.config import Config
from expanse.static.static import Static
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import ViewFactory


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.core.application import Application
    from expanse.routing.router import Router


class StaticServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(Static, self._register_static)

    def boot(self) -> None:
        self._container.on_resolved("router", self._add_static_route)
        self._container.on_resolved("view", self._register_view_globals)

    def _register_static(self, config: Config) -> Static:
        app: Application = self._container.make("app")
        paths: list[Path] = config.get("static.paths", [])
        paths = [app.base_path / p if not p.is_absolute() else p for p in paths]

        return Static(
            paths, prefix=config.get("static.prefix"), url=config.get("static.url")
        )

    def _add_static_route(self, router: "Router") -> None:
        config = self._container.make(Config)
        if config.get("app.debug", False):
            prefix: str = config["static.prefix"].rstrip("/")

            router.get(
                f"{prefix}/{{path:path}}",
                self._container.make(Static).get,
                name="static",
            )

    def _register_view_globals(self, view: ViewFactory) -> None:
        view.register_global(static=self._container.make(Static).url)
