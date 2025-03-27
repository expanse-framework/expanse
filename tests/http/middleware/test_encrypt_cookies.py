import json

from base64 import urlsafe_b64encode
from collections.abc import Callable

import pytest

from expanse.container.container import Container
from expanse.contracts.encryption.encryptor import Encryptor as EncryptorContract
from expanse.contracts.routing.router import Router as RouterContract
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.http.middleware.encrypt_cookies import EncryptCookies
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.router import Router


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


@pytest.fixture
def key_chain() -> KeyChain:
    return KeyChain([Key(SECRET)])


@pytest.fixture
def encryptor(key_chain: KeyChain) -> Encryptor:
    return Encryptor(key_chain, SALT)


@pytest.fixture
def container(encryptor: Encryptor) -> Container:
    container = Container()
    container.instance(EncryptorContract, encryptor)

    return container


@pytest.fixture
def router() -> RouterContract:
    return Router()


@pytest.fixture
def encrypt(encryptor: Encryptor) -> Callable[[str], str]:
    def _encrypt(value: str) -> str:
        message = encryptor.encrypt(value)

        return urlsafe_b64encode(json.dumps(message.dump()).encode()).decode()

    return _encrypt


def set_cookies() -> Response:
    response = Response("Hello, World!")
    response.with_cookie("name", "value")
    response.with_cookie("name2", "value2")
    response.with_cookie("name3", "value3")

    return response


def read_cookies(request: Request) -> Response:
    assert request.cookies["name"] == "value"
    assert request.cookies["name2"] == "value2"
    assert request.cookies["name3"] == "value3"

    return Response("Hello, World!")


async def test_response_cookies_are_encrypted(
    router: Router, container: Container, encrypt: Callable[[str], str]
) -> None:
    router.get("/", set_cookies).middleware(EncryptCookies)

    request = Request.create("http://localhost:8000", "GET")

    response = await router.handle(container, request)

    assert response.cookies["name"].name == "name"
    assert response.cookies["name"].value != "value"
    assert response.cookies["name2"].name == "name2"
    assert response.cookies["name2"].value != "value2"
    assert response.cookies["name3"].name == "name3"
    assert response.cookies["name3"].value != "value3"


async def test_request_cookies_are_decrypted(
    router: Router, container: Container, encrypt: Callable[[str], str]
) -> None:
    router.get("/", read_cookies).middleware(EncryptCookies)

    request = Request.create("http://localhost:8000", "GET")
    request.cookies["name"] = encrypt("value")
    request.cookies["name2"] = encrypt("value2")
    request.cookies["name3"] = encrypt("value3")

    container.instance(Request, request)

    await router.handle(container, request)


async def test_cookies_are_not_encrypted_if_they_are_disabled(
    router: Router, container: Container, encrypt: Callable[[str], str]
) -> None:
    router.get("/", set_cookies).middleware(EncryptCookies.excluding("name3"))

    request = Request.create("http://localhost:8000", "GET")

    response = await router.handle(container, request)

    assert response.cookies["name"].name == "name"
    assert response.cookies["name"].value != "value"
    assert response.cookies["name2"].name == "name2"
    assert response.cookies["name2"].value != "value2"
    assert response.cookies["name3"].name == "name3"
    assert response.cookies["name3"].value == "value3"


async def test_request_cookies_are_not_decrypted_if_they_are_disabled(
    router: Router, container: Container, encrypt: Callable[[str], str]
) -> None:
    router.get("/", read_cookies).middleware(EncryptCookies.excluding("name3"))

    request = Request.create("http://localhost:8000", "GET")
    request.cookies["name"] = encrypt("value")
    request.cookies["name2"] = encrypt("value2")
    request.cookies["name3"] = "value3"

    container.instance(Request, request)

    await router.handle(container, request)
