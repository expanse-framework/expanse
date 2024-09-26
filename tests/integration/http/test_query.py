from expanse.http.helpers import json
from expanse.http.query import Query
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from tests.integration.http.fixtures.request.models import FooModel


async def index_validated(query: Query[FooModel]) -> Response:
    return json({"bar": query.bar})


def test_simple_form_data_are_converted_if_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", index_validated)

    response = client.post("/?bar=42", data={"bar": "42"})

    assert response.json() == {"bar": 42}
