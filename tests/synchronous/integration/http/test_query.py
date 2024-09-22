from expanse.common.http.query import Query
from expanse.http.responder import Responder
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from tests.synchronous.integration.http.fixtures.request.models import FooModel


def index_validated(responder: Responder, query: Query[FooModel]) -> Response:
    return responder.json({"bar": query.bar})


def test_simple_form_data_are_converted_with_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", index_validated)

    response = client.post("/?bar=42", data={"bar": "42"})

    assert response.json() == {"bar": 42}
