from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.foundation.application import Application
from expanse.testing.test_client import TestClient


if TYPE_CHECKING:
    from expanse.routing.router import Router


@pytest.fixture()
def app() -> Application:
    application = Application()
    application.instance("config", {"app": {}})
    application.bootstrap_with([])

    return application


@pytest.fixture()
def router(app: Application) -> Router:
    return app.make("router")


@pytest.fixture()
def client(app: Application) -> TestClient:
    with TestClient(app) as client:
        yield client
