from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.static.static import Static
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_manager import ViewManager


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.core.application import Application
    from expanse.routing.router import Router


class StaticServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Static, self._register_static)

    async def boot(self) -> None:
        await self._container.on_resolved("router", self._add_static_route)
        await self._container.on_resolved("view:manager", self._register_view_globals)

    async def _register_static(self, config: Config) -> Static:
        app: Application = await self._container.get("app")
        paths: list[Path] = config.get("static.paths", [])
        paths = [app.base_path / p if not p.is_absolute() else p for p in paths]
        if (url := config.get("static.url")) is not None:
            url = str(url)

        return Static(paths, prefix=config.get("static.prefix"), url=url)

    async def _add_static_route(self, router: "Router") -> None:
        config = await self._container.get(Config)
        if config.get("app.debug", False):
            prefix: str = config["static.prefix"].rstrip("/")

            router.get(
                f"{prefix}/{{*path}}",
                (await self._container.get(Static)).get,
                name="static",
            )

    async def _register_view_globals(self, view: ViewManager) -> None:
        view.register_global(static=(await self._container.get(Static)).url)
