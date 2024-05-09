# ruff: noqa: I002

from expanse.core.application import Application
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


class ViewServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._register_factory()
        self._register_view_finder()

    def _register_factory(self) -> None:
        self._app.singleton(ViewFactory, self._create_factory)
        self._app.alias(ViewFactory, "view")

    def _create_factory(self, app: Application) -> ViewFactory:
        finder: ViewFinder = app.make("view:finder")

        return ViewFactory(finder, debug=app.config.get("app.debug", False))

    def _register_view_finder(self) -> None:
        def _create_view_finder(app: Application) -> ViewFinder:
            return ViewFinder(
                [
                    app.resolve_placeholder_path(path)
                    for path in app.config["view"]["paths"]
                ]
            )

        self._app.singleton(ViewFinder, _create_view_finder)
        self._app.alias(ViewFinder, "view:finder")
