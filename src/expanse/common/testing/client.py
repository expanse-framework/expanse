from httpx import BaseTransport
from httpx import Client as BaseClient

from expanse.common.core.application import Application


class TestClient(BaseClient):
    def __init__(self, app: Application, **kwargs) -> None:
        self.app = app

        if "transport" not in kwargs:
            kwargs["transport"] = self.transport

        super().__init__(**kwargs)

    @property
    def transport(self) -> BaseTransport | None:
        return
