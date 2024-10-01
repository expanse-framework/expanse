from expanse.http.form import Form
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from tests.integration.http.fixtures.request.models import FooModel


async def create_foo(form: Form) -> Response:
    return json({"bar": form.fields["bar"].value})


async def create_foo_validated(form: Form[FooModel]) -> Response:
    if form.is_submitted() and form.is_valid():
        assert form.data is not None

        return json({"bar": form.data.bar})

    return json({"errors": form.errors, "data": form.data})


def test_simple_form_data_are_not_converted_if_no_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo)

    response = client.post("/", data={"bar": "42"})

    assert response.json() == {"bar": "42"}


def test_simple_form_data_are_converted_if_validation_model(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo_validated)

    response = client.post("/", data={"bar": "42"})

    assert response.json() == {"bar": 42}


def test_validation_errors_are_correctly_handled(
    router: Router, client: TestClient
) -> None:
    router.post("/", create_foo_validated)

    response = client.post("/", data={"bar": "foo"})

    assert response.json() == {
        "data": None,
        "errors": [
            {
                "type": "int_parsing",
                "loc": ["bar"],
                "msg": (
                    "Input should be a valid integer, "
                    "unable to parse string as an integer"
                ),
                "input": "foo",
                "url": "https://errors.pydantic.dev/2.9/v/int_parsing",
            }
        ],
    }
