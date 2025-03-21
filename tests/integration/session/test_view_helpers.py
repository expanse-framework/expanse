from pathlib import Path

from treat.mock.mockery import Mockery

from expanse.contracts.routing.router import Router
from expanse.http.response import Response
from expanse.session.middleware.load_session import LoadSession
from expanse.session.middleware.validate_csrf_token import ValidateCSRFToken
from expanse.session.session import HTTPSession
from expanse.testing.client import TestClient
from expanse.view.view_factory import AsyncViewFactory
from expanse.view.view_factory import ViewFactory


def view(view: ViewFactory) -> Response:
    return view.render(view.make("csrf_token"))


async def async_view(view: AsyncViewFactory) -> Response:
    return await view.render(view.make("csrf_token"))


def test_crsf_token_helper_returns_the_current_csrf_token(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    client.app.config["session.store"] = "dictionary"

    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return(
        "foo-token"
    )
    client.app.config["view"] = {
        "paths": [Path(__file__).parent.joinpath("fixtures/views")]
    }
    router.get("/", view).middleware(LoadSession, ValidateCSRFToken)
    router.get("/async", async_view).middleware(LoadSession, ValidateCSRFToken)

    response = client.get("/")

    assert response.status_code == 200
    assert response.text == "foo-token"

    response = client.get("/async")

    assert response.status_code == 200
    assert response.text == "foo-token"
