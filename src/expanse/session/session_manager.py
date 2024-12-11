from typing import Any

from expanse.core.application import Application
from expanse.session.asynchronous.stores.store import AsyncStore
from expanse.session.config import StoresConfig
from expanse.session.session import HTTPSession
from expanse.session.synchronous.stores.store import Store
from expanse.support._utils import slugify


class SessionManager:
    def __init__(self, app: Application) -> None:
        self._app = app
        self._stores: dict[str, tuple[Store, AsyncStore]] = {}
        self._config = self._app.config.get("session", {})

    async def session(self) -> HTTPSession:
        stores = await self.stores()

        return HTTPSession(self.get_cookie_name(), *stores)

    async def stores(self, name: str | None = None) -> tuple[Store, AsyncStore]:
        name = name or self._config["store"]

        if name in self._stores:
            return self._stores[name]

        if name not in self._config["stores"]:
            raise RuntimeError(f"Session store {name} is not defined")

        raw_config = self._config.get("stores", {})
        config = StoresConfig.model_validate(raw_config)

        store = await self._create_stores(name, config)

        self._stores[name] = store

        return self._stores[name]

    async def _create_stores(
        self, name: str, config: StoresConfig
    ) -> tuple[Store, AsyncStore]:
        match name:
            case "dictionary":
                from expanse.session.asynchronous.stores.wrapper import (
                    AsyncWrapperStore,
                )
                from expanse.session.synchronous.stores.dict import DictStore

                store = DictStore(lifetime=self._config["lifetime"])

                return store, AsyncWrapperStore(store)
            case "database":
                from expanse.database.database_manager import AsyncDatabaseManager
                from expanse.database.database_manager import DatabaseManager
                from expanse.session.asynchronous.stores.database import (
                    AsyncDatabaseStore,
                )
                from expanse.session.synchronous.stores.database import DatabaseStore

                return DatabaseStore(
                    await self._app.container.get(DatabaseManager),
                    config.database.table,
                    self._config["lifetime"],
                    config.database.connection,
                ), AsyncDatabaseStore(
                    await self._app.container.get(AsyncDatabaseManager),
                    config.database.table,
                    self._config["lifetime"],
                    config.database.connection,
                )
            case "file":
                from expanse.session.asynchronous.stores.wrapper import (
                    AsyncWrapperStore,
                )
                from expanse.session.synchronous.stores.file import FileStore

                path = config.file.path
                if not path.is_absolute():
                    path = self._app.base_path.joinpath(path)

                file_store = FileStore(path, self._config["lifetime"])

                return file_store, AsyncWrapperStore(file_store)
            case "null":
                from expanse.session.asynchronous.stores.null import AsyncNullStore
                from expanse.session.synchronous.stores.null import NullStore

                return NullStore(), AsyncNullStore()
            case _:
                raise RuntimeError(f"Unsupported session store: {name}")

    def get_config(self) -> dict[str, Any]:
        return self._config

    def get_cookie_name(self) -> str:
        return self._config.get("cookie", f"{slugify(self._app.name)}_session")
