from typing import ClassVar

from expanse.encryption.encryption_manager import EncryptionManager
from expanse.encryption.errors import DecryptionError
from expanse.encryption.errors import MessageDecodeError
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class EncryptCookies:
    exclude: ClassVar[list[str]] = []

    def __init__(self, encryption: EncryptionManager):
        self._encryption: EncryptionManager = encryption
        self._exclude: list[str] = []

    @classmethod
    def excluding(cls, *cookies: str) -> type["EncryptCookies"]:
        klass = type(cls.__name__, (cls,), {"exclude": list(cookies)})

        return klass

    async def handle(self, request: Request, next: RequestHandler) -> Response:
        return self._encrypt(await next(self._decrypt(request)))

    def disable_for(self, *cookies: str) -> None:
        self._exclude.extend(cookies)

    def is_disabled(self, cookie: str) -> bool:
        return cookie in self._exclude or cookie in self.__class__.exclude

    def _encrypt(self, response: Response) -> Response:
        for name, cookie in response.cookies.items():
            if self.is_disabled(name):
                continue

            if cookie.value is None:
                continue

            value = self._encryption.encrypt(cookie.value)
            response.cookies[name] = cookie.with_value(value)

        return response

    def _decrypt(self, request: Request) -> Request:
        for key, value in request.cookies.items():
            if self.is_disabled(key):
                continue

            try:
                decrypted_value = self._encryption.decrypt(value)
                request.cookies[key] = decrypted_value
            except (MessageDecodeError, DecryptionError):
                request.cookies[key] = ""

                continue

        return request
