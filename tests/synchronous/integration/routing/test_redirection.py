from expanse.http.response import Response
from expanse.routing.responder import Responder
from expanse.routing.router import Router
from expanse.testing.client import TestClient


def destination() -> str:
    return "Arrived at destination"


def destination_with_parameters(name: str) -> str:
    return f"Arrived at {name} destination"


def redirection_to_url(responder: Responder) -> Response:
    return responder.redirect().to("/destination")


def redirection_to_named_route(responder: Responder) -> Response:
    return responder.redirect().to_route("destination")


def redirection_to_named_route_with_parameters(responder: Responder) -> Response:
    return responder.redirect().to_route("destination", {"name": "foo"})


def redirection_to_named_route_with_parameters_and_query_params(
    responder: Responder,
) -> Response:
    return responder.redirect().to_route(
        "destination", {"name": "foo", "foo": "bar", "bar": 42}
    )


def test_redirect_to_url(router: Router, client: TestClient) -> None:
    router.get("/destination", destination)
    router.get("/redirection", redirection_to_url)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == "Arrived at destination"


def test_redirect_to_named_route(router: Router, client: TestClient) -> None:
    router.get("/destination", destination, name="destination")
    router.get("/redirection", redirection_to_named_route)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == "Arrived at destination"


def test_redirect_to_named_route_with_parameters(
    router: Router, client: TestClient
) -> None:
    router.get("/destination/{name}", destination_with_parameters, name="destination")
    router.get("/redirection", redirection_to_named_route_with_parameters)

    response = client.get("/redirection", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/destination/foo"

    response = client.get("/redirection", follow_redirects=True)

    assert response.status_code == 200
    assert response.text == "Arrived at foo destination"


def test_redirect_to_named_route_with_parameters_and_query_params(
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
    assert response.text == "Arrived at foo destination"
