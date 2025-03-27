from enum import StrEnum

from expanse.contracts.routing.registrar import Registrar
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.testing.client import TestClient


def test_routes_are_matched_based_on_their_method(
    client: TestClient, router: Registrar
) -> None:
    router.get("/foo", lambda: Response("GET"))
    router.post("/foo", lambda: Response("POST"))

    response = client.get("/foo")
    assert response.status_code == 200
    assert response.text == "GET"

    response = client.post("/foo")
    assert response.status_code == 200
    assert response.text == "POST"


def test_static_routes_are_prioritized_over_dynamic_ones(
    client: TestClient, router: Registrar
) -> None:
    router.get("/foo/{bar}/baz", lambda: Response("DYNAMIC"))
    router.get("/foo/boom/baz", lambda: Response("STATIC"))

    response = client.get("/foo/bim/baz")
    assert response.status_code == 200
    assert response.text == "DYNAMIC"

    response = client.get("/foo/boom/baz")
    assert response.status_code == 200
    assert response.text == "STATIC"


def test_static_routes_are_differentiated_base_on_parameters_regex(
    client: TestClient, router: Registrar
) -> None:
    router.get(r"/foo/{bar:\w+}/baz", lambda bar: Response(bar))
    router.get(
        r"/foo/{bar:\d+}/baz",
        lambda bar: Response(bar, content_type="application/json"),
    )

    response = client.get("/foo/bim/baz")
    assert response.status_code == 200
    assert response.text == "bim"

    response = client.get("/foo/42/baz")
    assert response.status_code == 200
    assert response.json() == 42


def test_static_routes_are_differentiated_base_on_parameters_type(
    client: TestClient, router: Registrar
) -> None:
    class Foo(StrEnum):
        BAR = "bar"
        BAZ = "baz"

    def foo(bar: int) -> Response:
        return json(bar)

    def bar(value: Foo) -> Response:
        return json(value)

    router.get(r"/foo/{bar}/baz", foo)
    router.get(r"/foo/{value}/baz", bar)

    response = client.get("/foo/42/baz")
    assert response.status_code == 200
    assert response.json() == 42

    router.get(r"/foo/{value}/baz", bar)

    response = client.get("/foo/bar/baz")
    assert response.status_code == 200
    assert response.json() == "bar"
