from expanse.asynchronous.http.helpers import json
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from expanse.common.http.json import JSON
from tests.asynchronous.integration.http.fixtures.request.models import FooModel


async def create_foo(data: JSON) -> Response:
    return await json({"bar": data.data["bar"]})


async def create_foo_validated(form: JSON[FooModel]) -> Response:
    return await json({"bar": form.data.bar})


def test_simple_json_data_are_not_converted_if_no_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo)

    response = client.post("/", json={"bar": "42"})

    assert response.json() == {"bar": "42"}


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
                "loc": ["data", "bar"],
                "message": (
                    "Input should be a valid integer, "
                    "unable to parse string as an integer"
                ),
                "type": "int_parsing",
            }
        ],
    }
