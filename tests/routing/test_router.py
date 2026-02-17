import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.http.request import Request
from expanse.routing.route import Route
from expanse.routing.router import Router
from expanse.support.helpers import async_safe


async def test_router_warns_about_implicit_async_safe_status() -> None:
    config = Config({})

    def sync_endpoint() -> str:
        return "Hello, world!"

    router = Router(config)
    request = Request.create("http://example.com/test", method="GET")
    router.add_route(Route.get("/test", sync_endpoint))
    with pytest.warns(
        UserWarning,
        match=f"Synchronous function {sync_endpoint} is not explicitly declared",
    ):
        await router.handle(Container(), request)


@pytest.mark.parametrize("is_async_safe", [True, False])
async def test_router_does_not_warn_about_implicit_async_safe_status_if_explicit_declared(
    is_async_safe: bool, recwarn: pytest.WarningsRecorder
) -> None:
    config = Config({})

    @async_safe(is_async_safe)
    def sync_endpoint() -> str:
        return "Hello, world!"

    router = Router(config)
    request = Request.create("http://example.com/test", method="GET")
    router.add_route(Route.get("/test", sync_endpoint))

    await router.handle(Container(), request)

    assert recwarn.list == []


async def test_router_does_not_warn_about_implicit_async_safe_status_if_globally_disabled(
    recwarn: pytest.WarningsRecorder,
) -> None:
    config = Config({"app": {"warn_implicit_async_safe": False}})

    def sync_endpoint() -> str:
        return "Hello, world!"

    router = Router(config)
    request = Request.create("http://example.com/test", method="GET")
    router.add_route(Route.get("/test", sync_endpoint))

    await router.handle(Container(), request)

    assert recwarn.list == []
