# ruff: noqa: I002

from expanse.configuration.config import Config
from expanse.foundation.application import Application
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


class ViewServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_factory()
        await self._register_view_finder()

    async def _register_factory(self) -> None:
        self._app.singleton(ViewFactory, self._create_factory)
        self._app.alias(ViewFactory, "view")

    async def _create_factory(self, app: Application) -> ViewFactory:
        finder: ViewFinder = await app.make("view:finder")

        return ViewFactory(
            finder, debug=(await app.make(Config))["app"].get("debug", False)
        )

    async def _register_view_finder(self) -> None:
        async def _create_view_finder(app: Application) -> ViewFinder:
            return ViewFinder((await app.make(Config))["view"]["paths"])

        self._app.singleton("view:finder", _create_view_finder)
