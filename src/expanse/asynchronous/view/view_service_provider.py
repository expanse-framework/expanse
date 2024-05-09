# ruff: noqa: I002

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.asynchronous.view.view_finder import ViewFinder
from expanse.common.configuration.config import Config


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
            return ViewFinder(
                [
                    app.resolve_placeholder_path(path)
                    for path in (await app.make(Config))["view"]["paths"]
                ]
            )

        self._app.singleton(ViewFinder, _create_view_finder)
        self._app.alias(ViewFinder, "view:finder")
