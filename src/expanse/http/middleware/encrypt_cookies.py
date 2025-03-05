import base64
import json

from expanse.encryption.encryptor import Encryptor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.message import Message
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.types.http.middleware import RequestHandler


class EncryptCookies:
    def __init__(self, encryptor: Encryptor):
        self._encryptor = encryptor

    async def handle(self, request: Request, next: RequestHandler) -> Response:
        return self._encrypt(await next(self._decrypt(request)))

    def _encrypt(self, response: Response) -> Response:
        for cookie in response.cookies:
            message = self._encryptor.encrypt(cookie.value)
            cookie.value = base64.urlsafe_b64encode(
                json.dumps(message.dump()).encode()
            ).decode()

        return response

    def _decrypt(self, request: Request) -> Request:
        for key, value in request.cookies.items():
            raw_value = json.loads(base64.urlsafe_b64decode(value).decode())
            message = Message.load(raw_value)
            try:
                decrypted_value = self._encryptor.decrypt(message)
                request.cookies[key] = decrypted_value
            except DecryptionError:
                request.cookies[key] = None

                continue

        return request
