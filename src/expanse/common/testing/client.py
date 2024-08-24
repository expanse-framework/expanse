from typing import Generic
from typing import TypeVar

from httpx import BaseTransport
from httpx import Client as BaseClient

from expanse.common.core.application import Application


T = TypeVar("T", bound=Application)


class TestClient(BaseClient, Generic[T]):
    def __init__(self, app: T, **kwargs) -> None:
        self.app: T = app

        if "transport" not in kwargs:
            kwargs["transport"] = self.transport

        super().__init__(**kwargs)

    @property
    def transport(self) -> BaseTransport | None:
        return None
