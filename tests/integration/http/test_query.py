from expanse.http.query import Query
from expanse.http.response import Response
from expanse.routing.helpers import post
from expanse.routing.router import Router
from expanse.testing.test_client import TestClient
from tests.integration.http.fixtures.request.models import FooModel


def index(query: Query) -> Response:
    return Response.json({"bar": query.params["bar"]})


def index_validated(query: Query[FooModel]) -> Response:
    return Response.json({"bar": query.params.bar})


def test_simple_form_data_are_not_converted_if_no_validation_model(
    router: Router, client: TestClient
) -> None:
    router.add_route(post("/", index))

    response = client.post("/?bar=42", data={"bar": "42"})

    assert response.json() == {"bar": "42"}


def test_simple_form_data_are_converted_if_validation_model(
    router: Router, client: TestClient
) -> None:
    router.add_route(post("/", index_validated))

    response = client.post("/?bar=42", data={"bar": "42"})

    assert response.json() == {"bar": 42}
