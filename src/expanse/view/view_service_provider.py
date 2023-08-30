from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


if TYPE_CHECKING:
    from expanse.foundation.application import Application


class ViewServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._register_factory()
        self._register_view_finder()

    def _register_factory(self) -> None:
        self._app.singleton(
            ViewFactory,
            lambda app: self._create_factory(app),
        )
        self._app.alias(ViewFactory, "view")

    def _create_factory(self, app: Application) -> ViewFactory:
        finder: ViewFinder = app.make("view:finder")

        return ViewFactory(finder, debug=app.make("config")["app"].get("debug", False))

    def _register_view_finder(self) -> None:
        self._app.singleton(
            "view:finder",
            lambda app: ViewFinder(self._app.make("config")["view"]["paths"]),
        )
