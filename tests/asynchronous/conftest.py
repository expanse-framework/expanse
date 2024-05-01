from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.testing.client import TestClient


if TYPE_CHECKING:
    from expanse.asynchronous.routing.router import Router


@pytest.fixture()
async def app() -> Application:
    application = Application.configure(Path(__file__).parent.parent.parent).create()
    await application.bootstrap()

    application.config["app.debug"] = True

    return application


@pytest.fixture()
async def router(app: Application) -> Router:
    return await app.make("router")


@pytest.fixture()
def client(app: Application) -> TestClient:
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
