from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.core.application import Application
from expanse.http.middleware.trust_hosts import TrustHosts
from expanse.testing.client import TestClient


if TYPE_CHECKING:
    from collections.abc import Generator

    from expanse.contracts.routing.router import Router
    from expanse.core.http.middleware.middleware_stack import MiddlewareStack


@pytest.fixture()
def root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture()
async def unbootstrapped_app(root: Path) -> Application:
    async def configure_middleware(stack: MiddlewareStack) -> None:
        stack.use([TrustHosts])

    application = (
        Application.configure(root).with_middleware(configure_middleware).create()
    )

    return application


@pytest.fixture()
async def unbooted_app(unbootstrapped_app: Application) -> Application:
    await unbootstrapped_app.bootstrap()

    unbootstrapped_app.config["app.env"] = "test"

    return unbootstrapped_app


@pytest.fixture()
async def app(unbooted_app: Application) -> Application:
    await unbooted_app.boot()

    unbooted_app.config["app.debug"] = True
    unbooted_app.config["app.secret_key"] = "k" * 32
    unbooted_app.config["encryption.salt"] = "s" * 32

    return unbooted_app


@pytest.fixture()
async def router(app: Application) -> Router:
    return await app.container.get("router")


@pytest.fixture()
def client(app: Application) -> Generator[TestClient]:
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
