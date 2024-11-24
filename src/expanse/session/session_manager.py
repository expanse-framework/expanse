from typing import Any

from expanse.core.application import Application
from expanse.session.asynchronous.stores.store import AsyncStore
from expanse.session.asynchronous.stores.wrapper import AsyncWrapperStore
from expanse.session.session import HTTPSession
from expanse.session.synchronous.stores.store import Store
from expanse.support._utils import slugify


class SessionManager:
    def __init__(self, app: Application) -> None:
        self._app = app
        self._stores: dict[str, tuple[Store, AsyncStore]] = {}
        self._config = self._app.config.get("session", {})

    async def session(self) -> HTTPSession:
        stores = await self.stores(self.get_config()["store"])

        return HTTPSession(self.get_cookie_name(), *stores)

    async def stores(self, name: str) -> tuple[Store, AsyncStore]:
        if name in self._stores:
            return self._stores[name]

        store = await self._create_stores(name)

        self._stores[name] = store

        return self._stores[name]

    async def _create_stores(self, name: str) -> tuple[Store, AsyncStore]:
        match name:
            case "dict":
                from expanse.session.synchronous.stores.dict import DictStore

                store = DictStore()

                return store, AsyncWrapperStore(store)
            case "database":
                from expanse.database.database_manager import AsyncDatabaseManager
                from expanse.database.database_manager import DatabaseManager
                from expanse.session.asynchronous.stores.database import (
                    AsyncDatabaseStore,
                )
                from expanse.session.synchronous.stores.database import DatabaseStore

                config = self.get_config()

                return DatabaseStore(
                    await self._app.container.get(DatabaseManager),
                    config["database_table"],
                    config["lifetime"],
                    config["database_connection"],
                ), AsyncDatabaseStore(
                    await self._app.container.get(AsyncDatabaseManager),
                    config["database_table"],
                    config["lifetime"],
                    config["database_connection"],
                )
            case _:
                raise RuntimeError(f"Unsupported session store driver: {name}")

    def get_config(self) -> dict[str, Any]:
        return self._config

    def get_cookie_name(self) -> str:
        return self._config.get("cookie", f"{slugify(self._app.name)}_session")
