from abc import ABC
from abc import abstractmethod

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine

from expanse.asynchronous.contracts.database.connection import Connection
from expanse.asynchronous.contracts.database.session import Session


class DatabaseManager(ABC):
    @abstractmethod
    def connection(self, name: str | None = None) -> Connection: ...

    @abstractmethod
    def session(self, name: str | None = None) -> Session: ...

    @abstractmethod
    def create_base_engine(self, url: URL) -> AsyncEngine: ...
