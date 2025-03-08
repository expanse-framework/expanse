import base64
import json

from typing import ClassVar

from expanse.encryption.encryptor import Encryptor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.message import Message
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class EncryptCookies:
    exclude: ClassVar[list[str]] = []

    def __init__(self, encryptor: Encryptor):
        self._encryptor = encryptor
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
        for cookie in response.cookies:
            if self.is_disabled(cookie.name):
                continue

            message = self._encryptor.encrypt(cookie.value)
            cookie.value = base64.urlsafe_b64encode(
                json.dumps(message.dump()).encode()
            ).decode()

        return response

    def _decrypt(self, request: Request) -> Request:
        for key, value in request.cookies.items():
            if self.is_disabled(key):
                continue

            try:
                raw_value = json.loads(base64.urlsafe_b64decode(value).decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                request.cookies[key] = ""

                continue

            message = Message.load(raw_value)
            try:
                decrypted_value = self._encryptor.decrypt(message)
                request.cookies[key] = decrypted_value
            except DecryptionError:
                request.cookies[key] = ""

                continue

        return request
