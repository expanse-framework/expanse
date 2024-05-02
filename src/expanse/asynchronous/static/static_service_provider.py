from typing import TYPE_CHECKING

from expanse.asynchronous.static.static import Static
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.common.configuration.config import Config


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.asynchronous.routing.router import Router


class StaticServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._app.singleton(Static, self._register_static)

    async def boot(self) -> None:
        await self._app.on_resolved("router", self._add_static_route)
        await self._app.on_resolved("view", self._register_view_globals)

    def _register_static(self, config: Config) -> Static:
        paths: list[Path] = [
            self._app.resolve_placeholder_path(p)
            for p in config.get("static.paths", [])
        ]

        return Static(
            paths, prefix=config.get("static.prefix"), url=config.get("static.url")
        )

    async def _add_static_route(self, router: "Router") -> None:
        if self._app.config.get("app.debug", False):
            prefix: str = self._app.config["static.prefix"].rstrip("/")

            router.get(
                f"{prefix}/{{path:path}}",
                (await self._app.make(Static)).get,
                name="static",
            )

    async def _register_view_globals(self, view: ViewFactory) -> None:
        view.register_global(static=(await self._app.make(Static)).url)
