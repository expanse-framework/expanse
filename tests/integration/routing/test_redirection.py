from expanse.http.helpers import redirect
from expanse.http.redirect import Redirect
from expanse.http.responder import AsyncResponder
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient


async def destination() -> str:
    return "Arrived at destination"


async def destination_with_parameters(name: str) -> str:
    return f"Arrived at {name} destination"


async def redirection_to_url(responder: AsyncResponder) -> Response:
    return responder.redirect().to("/destination")


async def redirection_to_named_route(redirect: Redirect) -> Response:
    return redirect.to_route("destination")


async def redirection_to_named_route_with_parameters() -> Response:
    return (await redirect()).to_route("destination", {"name": "foo"})


async def redirection_to_named_route_with_parameters_and_query_params(
    redirect: Redirect,
) -> Response:
    return redirect.to_route("destination", {"name": "foo", "foo": "bar", "bar": 42})


async def test_redirect_to_url(router: Router, client: TestClient) -> None:
    router.get("/destination", destination)
    router.get("/redirection", redirection_to_url)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == '"Arrived at destination"'


async def test_redirect_to_named_route(router: Router, client: TestClient) -> None:
    router.get("/destination", destination, name="destination")
    router.get("/redirection", redirection_to_named_route)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == '"Arrived at destination"'


async def test_redirect_to_named_route_with_parameters(
    router: Router, client: TestClient
) -> None:
    router.get("/destination/{name}", destination_with_parameters, name="destination")
    router.get("/redirection", redirection_to_named_route_with_parameters)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination/foo"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == '"Arrived at foo destination"'


async def test_redirect_to_named_route_with_parameters_and_query_params(
    router: Router, client: TestClient
) -> None:
    router.get("/destination/{name}", destination_with_parameters, name="destination")
    router.get(
        "/redirection", redirection_to_named_route_with_parameters_and_query_params
    )

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination/foo?foo=bar&bar=42"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == '"Arrived at foo destination"'
