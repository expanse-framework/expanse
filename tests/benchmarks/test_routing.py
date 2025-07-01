from pytest_codspeed.plugin import BenchmarkFixture

from expanse.contracts.routing.router import Router
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.helpers import get
from expanse.testing.client import TestClient


@get("/", name="index")
async def index() -> Response:
    return json({"message": "Hello world!"})


class Controller:
    @get("/controller", name="controller")
    async def controller(self) -> Response:
        return json({"message": "Hello from controller!"})


def test_simple_routes(
    router: Router, client: TestClient, benchmark: BenchmarkFixture
) -> None:
    router.handler(index)

    benchmark(client.get, "/")


def test_controller_route(
    router: Router, client: TestClient, benchmark: BenchmarkFixture
) -> None:
    router.controller(Controller)

    benchmark(client.get, "/controller")
