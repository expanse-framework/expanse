from abc import ABC
from abc import abstractmethod

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine

from expanse.contracts.database.asynchronous.connection import AsyncConnection
from expanse.contracts.database.asynchronous.session import AsyncSession


class AsyncDatabaseManager(ABC):
    @abstractmethod
    def connection(self, name: str | None = None) -> AsyncConnection:
        ...

    @abstractmethod
    def session(self, name: str | None = None) -> AsyncSession:
        ...

    @abstractmethod
    async def create_base_engine(self, url: URL) -> AsyncEngine:
        ...
