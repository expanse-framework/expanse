import pytest

from treat.mock import Mockery

from expanse.contracts.encryption.encryptor import Encryptor as EncryptorContract
from expanse.core.application import Application
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.session.middleware.load_session import LoadSession
from expanse.session.middleware.validate_csrf_token import ValidateCSRFToken
from expanse.session.session import HTTPSession
from expanse.testing.client import TestClient


@pytest.fixture(autouse=True)
def configure_app(app: Application) -> None:
    app.config["session.store"] = "dictionary"


async def handler() -> Response:
    return Response("Foo")


def test_middleware_is_passthrough_for_read_queries(
    client: TestClient, router: Router
) -> None:
    router.get("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.get("/")

    assert response.status_code == 200
    assert response.text == "Foo"


async def test_middleware_adds_xsrf_token_for_read_queries(
    client: TestClient, router: Router
) -> None:
    router.get("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.get("/")

    assert response.status_code == 200
    assert response.text == "Foo"
    assert response.cookies["XSRF-TOKEN"] is not None


async def test_middleware_retrieves_token_from_form_data(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post("/", data={"_token": "foo"})

    assert response.status_code == 200
    assert response.text == "Foo"
    assert response.cookies["XSRF-TOKEN"] is not None


async def test_middleware_retrieves_token_from_json_data(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post("/", json={"_token": "foo"})

    assert response.status_code == 200
    assert response.text == "Foo"
    assert response.cookies["XSRF-TOKEN"] is not None


async def test_middleware_retrieves_token_from_query_string(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post("/", params={"_token": "foo"}, json={})

    assert response.status_code == 200
    assert response.text == "Foo"
    assert response.cookies["XSRF-TOKEN"] is not None


async def test_middleware_retrieves_token_from_xsrf_header(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    encryptor = Encryptor(KeyChain([Key(b"b" * 32)]), b"s" * 32)
    client.app.container.instance(EncryptorContract, encryptor)

    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post(
        "/",
        json={},
        headers={"X-XSRF-TOKEN": encryptor.encrypt("foo").dump("base64")},
    )

    assert response.status_code == 200
    assert response.text == "Foo"
    assert response.cookies["XSRF-TOKEN"] is not None


async def test_middleware_should_raise_an_error_on_token_mismatch(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post("/", data={"_token": "bar"})

    assert response.status_code == 419
    assert "XSRF-TOKEN" not in response.cookies


async def test_middleware_should_raise_an_error_on_token_mismatch_for_json(
    client: TestClient, router: Router, mockery: Mockery
) -> None:
    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post(
        "/", json={"_token": "bar"}, headers={"Accept": "application/json"}
    )

    assert response.status_code == 419
    assert response.json() == {
        "exception": "HTTPException",
        "message": "CSRF token mismatch",
    }
    assert "XSRF-TOKEN" not in response.cookies
