from collections.abc import Callable

import pytest

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.encryption.encryptor_factory import (
    EncryptorFactory as EncryptorFactoryContract,
)
from expanse.contracts.routing.router import Router as RouterContract
from expanse.encryption.encryption_manager import EncryptionManager
from expanse.encryption.encryptor import Encryptor
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.http.middleware.encrypt_cookies import EncryptCookies
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.router import Router


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


class EncryptorFactory(EncryptorFactoryContract):
    def __init__(self, key_chain: KeyChain, salt: bytes) -> None:
        self._key_chain = key_chain
        self._salt = salt

    def make(self, compress: bool = True, purpose: bytes | None = None) -> "Encryptor":
        return Encryptor(
            self._key_chain, salt=self._salt, purpose=purpose, compress=compress
        )


@pytest.fixture
def key_chain() -> KeyChain:
    return KeyChain([Key(SECRET)])


@pytest.fixture
def encryption(key_chain: KeyChain) -> EncryptionManager:
    return EncryptionManager(EncryptorFactory(key_chain, SALT))


@pytest.fixture
def container(encryption: EncryptionManager) -> Container:
    container = Container()
    container.instance(EncryptionManager, encryption)

    return container


@pytest.fixture
def router() -> RouterContract:
    return Router(Config({}))


@pytest.fixture
def encrypt(encryption: EncryptionManager) -> Callable[[str], str]:
    def _encrypt(value: str) -> str:
        return encryption.encrypt(value)

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
