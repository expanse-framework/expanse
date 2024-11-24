import pendulum
import pytest

from expanse.core.application import Application
from expanse.http.helpers import json
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.session.middleware.load_session import LoadSession
from expanse.session.session_service_provider import SessionServiceProvider
from expanse.testing.client import TestClient
from expanse.testing.command_tester import CommandTester


@pytest.mark.parametrize(
    "store", ["dictionary", pytest.param("database", marks=pytest.mark.db)]
)
def test_session_is_managed_for_each_request(
    app: Application,
    router: Router,
    client: TestClient,
    store: str,
    command_tester: CommandTester,
) -> None:
    app.register(SessionServiceProvider)
    app.config["session"]["store"] = store
    app.config["database"]["default"] = "sqlite"

    command = command_tester.command("db migrate")
    command.run()

    def session_test(request: Request) -> Response:
        request.session.set("foo", "bar")
        if request.query_params.get("flash"):
            request.session.flash("baz", 42)

        return json(
            {k: v for k, v in request.session.all().items() if not k.startswith("_")}
        )

    router.get("/session", session_test).middleware(LoadSession)

    now = pendulum.now("UTC")
    with pendulum.travel_to(now).freeze():
        response = client.get("/session?flash=1")
        cookie = next(iter(response.cookies.jar))

    assert response.json() == {"baz": 42, "foo": "bar"}
    assert cookie.value != ""
    assert cookie.name == "expanse_session"
    assert cookie.domain is not None
    assert cookie.path == "/"
    assert (
        cookie.expires
        == now.add(minutes=app.config["session"]["lifetime"]).int_timestamp
    )

    # Flash data will still be available but on the next save it will be removed
    response = client.get("/session", cookies=response.cookies)

    # Flash data is no longer available
    response = client.get("/session", cookies=response.cookies)

    assert response.json() == {"foo": "bar"}
    assert response.cookies["expanse_session"] == cookie.value


@pytest.mark.parametrize(
    "store", ["dictionary", pytest.param("database", marks=pytest.mark.db)]
)
def test_session_can_be_set_to_be_cleared_with_the_browser(
    app: Application,
    router: Router,
    client: TestClient,
    store: str,
    command_tester: CommandTester,
) -> None:
    app.register(SessionServiceProvider)
    app.config["session"]["store"] = store
    app.config["database"]["default"] = "sqlite"
    app.config["session"]["clear_with_browser"] = True

    command = command_tester.command("db migrate")
    command.run()

    def session_test(request: Request) -> Response:
        request.session.set("foo", "bar")
        if request.query_params.get("flash"):
            request.session.flash("baz", 42)

        return json(
            {k: v for k, v in request.session.all().items() if not k.startswith("_")}
        )

    router.get("/session", session_test).middleware(LoadSession)

    now = pendulum.now("UTC")
    with pendulum.travel_to(now).freeze():
        response = client.get("/session?flash=1")
        cookie = next(iter(response.cookies.jar))

    assert response.json() == {"baz": 42, "foo": "bar"}
    assert cookie.value != ""
    assert cookie.name == "expanse_session"
    assert cookie.domain is not None
    assert cookie.path == "/"
    assert cookie.expires is None
