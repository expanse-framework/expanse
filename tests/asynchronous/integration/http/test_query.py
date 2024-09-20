from expanse.asynchronous.http.helpers import json
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.common.http.query import Query
from tests.asynchronous.integration.http.fixtures.request.models import FooModel


async def index_validated(query: Query[FooModel]) -> Response:
    return await json({"bar": query.bar})


def test_simple_form_data_are_converted_if_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", index_validated)

    response = client.post("/?bar=42", data={"bar": "42"})

    assert response.json() == {"bar": 42}
