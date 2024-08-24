from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.testing.client import TestClient


if TYPE_CHECKING:
    from collections.abc import Generator

    from expanse.asynchronous.core.http.middleware.middleware_stack import (
        MiddlewareStack,
    )
    from expanse.asynchronous.routing.router import Router


@pytest.fixture()
def root() -> Path:
    return Path(__file__).parent.parent.parent


@pytest.fixture()
async def app(root: Path) -> Application:
    async def configure_middleware(stack: MiddlewareStack) -> None:
        stack.use([])

    application = (
        Application.configure(root).with_middleware(configure_middleware).create()
    )

    await application.bootstrap()

    application.config["app.debug"] = True

    return application


@pytest.fixture()
async def router(app: Application) -> Router:
    return await app.container.make("router")


@pytest.fixture()
def client(app: Application) -> Generator[TestClient]:
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
