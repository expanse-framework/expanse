from expanse.asynchronous.http.response import Response
from expanse.asynchronous.http.response_adapter import ResponseAdapter
from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.asynchronous.view.view import View
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.asynchronous.view.view_finder import ViewFinder
from expanse.common.configuration.config import Config


class ViewServiceProvider(ServiceProvider):
    async def register(self) -> None:
        await self._register_factory()
        await self._register_view_finder()

    async def boot(self) -> None:
        await self._container.on_resolved(
            ResponseAdapter, self._register_response_adapters
        )

    async def _register_factory(self) -> None:
        self._container.singleton(ViewFactory, self._create_factory)
        self._container.alias(ViewFactory, "view")

    async def _create_factory(self, finder: ViewFinder, config: Config) -> ViewFactory:
        return ViewFactory(finder, debug=config["app"].get("debug", False))

    async def _register_view_finder(self) -> None:
        async def _create_view_finder(config: Config) -> ViewFinder:
            return ViewFinder(config["view"]["paths"])

        self._container.singleton(ViewFinder, _create_view_finder)
        self._container.alias(ViewFinder, "view:finder")

    async def _register_response_adapters(self, adapter: ResponseAdapter) -> None:
        async def adapt_view(raw_response: View, factory: ViewFactory) -> Response:
            return await factory.render(raw_response)

        adapter.register_adapter(View, adapt_view)
