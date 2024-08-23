from typing import TYPE_CHECKING

from expanse.asynchronous.static.static import Static
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.common.configuration.config import Config


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.asynchronous.core.application import Application
    from expanse.asynchronous.routing.router import Router


class StaticServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Static, self._register_static)

    async def boot(self) -> None:
        await self._container.on_resolved("router", self._add_static_route)
        await self._container.on_resolved("view", self._register_view_globals)

    async def _register_static(self, config: Config) -> Static:
        app: Application = await self._container.make("app")
        paths: list[Path] = config.get("static.paths", [])
        paths = [app.base_path / p if not p.is_absolute() else p for p in paths]

        return Static(
            paths, prefix=config.get("static.prefix"), url=config.get("static.url")
        )

    async def _add_static_route(self, router: "Router") -> None:
        config = await self._container.make(Config)
        if config.get("app.debug", False):
            prefix: str = config["static.prefix"].rstrip("/")

            router.get(
                f"{prefix}/{{path:path}}",
                (await self._container.make(Static)).get,
                name="static",
            )

    async def _register_view_globals(self, view: ViewFactory) -> None:
        view.register_global(static=(await self._container.make(Static)).url)
