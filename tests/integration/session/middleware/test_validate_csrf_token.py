import pytest

from treat.mock import Mockery

from expanse.contracts.encryption.encryptor_factory import (
    EncryptorFactory as EncryptorFactoryContract,
)
from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.encryption.encryption_manager import EncryptionManager
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.http.response import Response
from expanse.session.middleware.load_session import LoadSession
from expanse.session.middleware.validate_csrf_token import ValidateCSRFToken
from expanse.session.session import HTTPSession
from expanse.testing.client import TestClient


class EncryptorFactory(EncryptorFactoryContract):
    def __init__(self, key_chain: KeyChain, salt: bytes) -> None:
        self._key_chain = key_chain
        self._salt = salt

    def make(
        self,
        compress: bool = True,
        purpose: bytes | None = None,
    ) -> "Encryptor":
        return Encryptor(
            self._key_chain, salt=self._salt, purpose=purpose, compress=compress
        )


@pytest.fixture
def key_chain() -> KeyChain:
    return KeyChain([Key(b"s" * 32)])


@pytest.fixture
def encryption(key_chain: KeyChain) -> EncryptionManager:
    return EncryptionManager(EncryptorFactory(key_chain, b"s" * 32))


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
    client: TestClient, router: Router, mockery: Mockery, encryption: EncryptionManager
) -> None:
    client.app.container.instance(EncryptionManager, encryption)

    mockery.mock(HTTPSession).should_receive("_generate_csrf_token").and_return("foo")

    router.post("/", handler).middleware(LoadSession, ValidateCSRFToken)

    response = client.post(
        "/",
        json={},
        headers={"X-XSRF-TOKEN": encryption.encrypt("foo")},
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
