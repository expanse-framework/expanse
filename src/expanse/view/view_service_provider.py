from expanse.common.configuration.config import Config
from expanse.http.response import Response
from expanse.http.response_adapter import ResponseAdapter
from expanse.support.service_provider import ServiceProvider
from expanse.view.view import View
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


class ViewServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._register_factory()
        self._register_view_finder()

    def boot(self) -> None:
        self._container.on_resolved(ResponseAdapter, self._register_response_adapters)

    def _register_factory(self) -> None:
        self._container.singleton(ViewFactory, self._create_factory)
        self._container.alias(ViewFactory, "view")

    def _create_factory(self, finder: ViewFinder, config: Config) -> ViewFactory:
        return ViewFactory(finder, debug=config.get("app.debug", False))

    def _register_view_finder(self) -> None:
        def _create_view_finder(config: Config) -> ViewFinder:
            return ViewFinder(config["view"]["paths"])

        self._container.singleton(ViewFinder, _create_view_finder)
        self._container.alias(ViewFinder, "view:finder")

    def _register_response_adapters(self, adapter: ResponseAdapter) -> None:
        def adapt_view(raw_response: View, factory: ViewFactory) -> Response:
            return factory.render(raw_response)

        adapter.register_adapter(View, adapt_view)
