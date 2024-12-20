from pathlib import Path

from expanse.core.application import Application
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from expanse.view.synchronous.view_factory import ViewFactory
from expanse.view.view import View


def get_request_local_view(view: ViewFactory) -> View:
    return view.make("request_local")


def test_request_is_registered_as_a_view_local(
    app: Application, router: Router, client: TestClient
) -> None:
    app.config["view.paths"].append(Path("tests/integration/http/fixtures/views"))

    router.get("/", get_request_local_view)

    response = client.get("/", headers={"X-Request-ID": "123"})

    assert response.text == "123"
