from expanse.contracts.routing.router import Router
from expanse.http.helpers import json
from expanse.http.json import JSON
from expanse.http.response import Response
from expanse.testing.client import TestClient
from tests.integration.http.fixtures.request.models import FooModel


async def create_foo_validated(form: JSON[FooModel]) -> Response:
    return json({"bar": form.bar})


def test_simple_json_data_are_converted_if_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo_validated)

    response = client.post("/", json={"bar": "42"})

    assert response.json() == {"bar": 42}


def test_validation_errors_are_correctly_reported(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo_validated)

    response = client.post("/", json={"bar": "foo"})

    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "detail": [
            {
                "loc": ["bar"],
                "message": (
                    "Input should be a valid integer, "
                    "unable to parse string as an integer"
                ),
                "type": "int_parsing",
            }
        ],
    }
