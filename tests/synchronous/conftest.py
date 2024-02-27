from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.common.configuration.config import Config
from expanse.foundation.application import Application
from expanse.testing.client import TestClient


if TYPE_CHECKING:
    from expanse.routing.router import Router


@pytest.fixture()
def app() -> Application:
    application = Application.configure(Path(__file__).parent.parent.parent).create()
    application.set_config(Config({"app": {}}))
    application.bootstrap()

    return application


@pytest.fixture()
def router(app: Application) -> Router:
    return app.make("router")


@pytest.fixture()
def client(app: Application) -> TestClient:
    with TestClient(app=app) as client:
        yield client
