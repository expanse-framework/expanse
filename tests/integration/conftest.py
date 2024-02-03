from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.configuration.config import Config
from expanse.foundation.application import Application
from expanse.testing.test_client import TestClient


if TYPE_CHECKING:
    from expanse.routing.router import Router


@pytest.fixture()
async def app() -> Application:
    application = Application()
    application.instance(Config, Config({"app": {}}))
    application.alias(Config, "config")
    await application.bootstrap_with([])

    return application


@pytest.fixture()
async def router(app: Application) -> Router:
    return await app.make("router")


@pytest.fixture()
def client(app: Application) -> TestClient:
    with TestClient(app) as client:
        yield client
