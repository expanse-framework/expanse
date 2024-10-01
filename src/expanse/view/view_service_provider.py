from expanse.configuration.config import Config
from expanse.http.response import Response
from expanse.http.response_adapter import ResponseAdapter
from expanse.support.service_provider import ServiceProvider
from expanse.view.view import View
from expanse.view.view_factory import AsyncViewFactory
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder
from expanse.view.view_manager import ViewManager


class ViewServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_sync()
        await self._register_async()
        await self._register_view_finder()
        self._container.singleton(ViewManager)
        self._container.alias(ViewManager, "view:manager")

    async def _register_sync(self) -> None:
        await self._register_factory()

    async def _register_async(self) -> None:
        await self._register_async_factory()

    async def boot(self) -> None:
        await self._container.on_resolved(
            ResponseAdapter, self._register_response_adapters
        )

    async def _register_factory(self) -> None:
        self._container.scoped(ViewFactory, self._create_factory)
        self._container.alias(ViewFactory, "view")

    async def _register_async_factory(self) -> None:
        self._container.scoped(AsyncViewFactory, self._create_async_factory)
        self._container.alias(AsyncViewFactory, "view:async")

    async def _create_factory(self, manager: ViewManager) -> ViewFactory:
        return ViewFactory(manager)

    async def _create_async_factory(self, manager: ViewManager) -> AsyncViewFactory:
        return AsyncViewFactory(manager)

    async def _register_view_finder(self) -> None:
        async def _create_view_finder(config: Config) -> ViewFinder:
            return ViewFinder(config["view"]["paths"])

        self._container.singleton(ViewFinder, _create_view_finder)
        self._container.alias(ViewFinder, "view:finder")

    async def _register_response_adapters(self, adapter: ResponseAdapter) -> None:
        async def adapt_view(raw_response: View, factory: AsyncViewFactory) -> Response:
            return await factory.render(raw_response)

        adapter.register_adapter(View, adapt_view)
