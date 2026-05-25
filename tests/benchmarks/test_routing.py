import pytest

from httpx import Response as HTTPXResponse
from pytest_codspeed.plugin import BenchmarkFixture

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.helpers import get
from expanse.support.service_provider import ServiceProvider
from expanse.testing.client import TestClient


class Dependency:
    def __init__(self, value: str) -> None:
        self.value = value


class ScopedDependency:
    def __init__(self, dependency: Dependency, value: str) -> None:
        self.value = f"scoped: {value}, dependency: {dependency.value}"


class TestServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Dependency, self.create_dependency)
        self._container.scoped(ScopedDependency, self.create_scoped_dependency)

    async def create_dependency(self) -> Dependency:
        return Dependency("dependency value")

    async def create_scoped_dependency(
        self, dependency: Dependency
    ) -> ScopedDependency:
        return ScopedDependency(dependency, "scoped value")


@get("/", name="index")
async def index() -> Response:
    return json({"message": "Hello world!"})


@get("/async/deps", name="async.deps")
async def async_deps(
    dependency: Dependency, scoped_dependency: ScopedDependency
) -> Response:
    return json({"message": f"{dependency.value}, {scoped_dependency.value}"})


class Controller:
    @get("/controller", name="controller")
    async def controller(self) -> Response:
        return json({"message": "Hello from controller!"})


def _request(
    client: TestClient, path: str, benchmark: BenchmarkFixture, method: str = "GET"
) -> HTTPXResponse:
    # Warmup
    response = client.request(method, path)

    assert response.is_success

    def execute() -> HTTPXResponse:
        return client.request(method, path)

    return benchmark(execute)


@pytest.fixture(autouse=True)
async def setup(app: Application) -> None:
    await app.register(TestServiceProvider(app.container))


def test_simple_routes(
    router: Router, client: TestClient, benchmark: BenchmarkFixture
) -> None:
    router.handler(index)

    response = _request(client, "/", benchmark)

    assert response.status_code == 200
    assert response.json() == {"message": "Hello world!"}


def test_controller_route(
    router: Router, client: TestClient, benchmark: BenchmarkFixture
) -> None:
    router.controller(Controller)

    response = _request(client, "/controller", benchmark)

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from controller!"}


def test_async_dependencies(
    router: Router, client: TestClient, benchmark: BenchmarkFixture
) -> None:
    router.handler(async_deps)

    response = _request(client, "/async/deps", benchmark)

    assert response.status_code == 200
    assert response.json() == {
        "message": "dependency value, scoped: scoped value, dependency: dependency value"
    }
