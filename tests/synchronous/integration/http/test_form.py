from expanse.http.form import Form
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from tests.synchronous.integration.http.fixtures.request.models import FooModel


def create_foo(form: Form) -> Response:
    return Response.json({"bar": form.data["bar"]})


def create_foo_validated(form: Form[FooModel]) -> Response:
    return Response.json({"bar": form.data.bar})


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
