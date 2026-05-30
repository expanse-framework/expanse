from __future__ import annotations

import pickle
import time

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from sqlalchemy import CursorResult
from sqlalchemy import Select
from sqlalchemy import TableClause
from sqlalchemy import case
from sqlalchemy import column
from sqlalchemy import exists
from sqlalchemy import select
from sqlalchemy import table

from expanse.contracts.cache.cache_item import CacheItem
from expanse.contracts.cache.synchronous.store import Store


if TYPE_CHECKING:
    from expanse.cache.config.database import DatabaseStoreConfig
    from expanse.contracts.lock.synchronous.lock import Lock
    from expanse.database.synchronous.database_manager import DatabaseManager


class DatabaseStore(Store):
    def __init__(self, config: DatabaseStoreConfig, db: DatabaseManager) -> None:
        self._config: DatabaseStoreConfig = config
        self._db: DatabaseManager = db
        self._table: TableClause = table(
            self._config.table, column("key"), column("data"), column("expiration")
        )

    @override
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return self.set_many({key: value}, ttl)

    @override
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        now = int(time.time())
        values = [
            {
                "key": key,
                "data": pickle.dumps(value),
                "expiration": now + ttl if ttl is not None else None,
            }
            for key, value in items.items()
        ]

        engine = self._db.configure_engine(self._config.connection)

        match engine.dialect.name:
            case "sqlite":
                self._sqlite_upsert(values)
            case "postgresql":
                self._postgres_upsert(values)
            case "mysql":
                self._mysql_upsert(values)
            case _:
                with self._db.connection(self._config.connection) as connection:
                    for value in values:
                        key_exists = (
                            connection.execute(
                                select(
                                    exists()
                                    .select_from(self._table)
                                    .where(column("key") == value["key"])
                                )
                            )
                        ).scalar()
                        if key_exists:
                            connection.execute(
                                self._table.update()
                                .where(column("key") == value["key"])
                                .values(**value)
                            )
                        else:
                            connection.execute(self._table.insert().values(**value))

                    connection.commit()

        return True

    @override
    def get(self, key: str) -> CacheItem:
        return self.get_many([key])[key]

    @override
    def get_many(self, keys: list[str]) -> dict[str, CacheItem]:
        if not keys:
            return {}

        now = int(time.time())
        expired: list[str] = []
        items: dict[str, CacheItem] = {key: CacheItem(key=key) for key in keys}
        with self._db.connection(self._config.connection) as connection:
            stmt: Select[tuple[str, bytes | None]] = (
                select(
                    column("key"),
                    case(
                        (column("expiration").is_(None), column("data")),
                        (column("expiration") > now, column("data")),
                        else_=None,
                    ),
                )
                .select_from(self._table)
                .where(column("key").in_(keys))
            )
            results: CursorResult[tuple[str, bytes | None]] = connection.execute(stmt)
            rows = results.fetchall()

            for row in rows:
                key, data = row
                if data is not None:
                    items[key] = CacheItem(
                        key=key, value=pickle.loads(data), is_hit=True
                    )
                else:
                    expired.append(key)

            if expired:
                connection.execute(
                    self._table.delete().where(column("key").in_(expired))
                )

            connection.commit()

        return items

    @override
    def has(self, key: str) -> bool:
        now = int(time.time())
        with self._db.connection(self._config.connection) as connection:
            result = connection.execute(
                select(
                    exists()
                    .select_from(self._table)
                    .where(
                        column("key") == key,
                        (column("expiration").is_(None)) | (column("expiration") > now),
                    )
                )
            )

            return result.scalar_one()

    @override
    def delete(self, key: str) -> bool:
        with self._db.connection(self._config.connection) as connection:
            connection.execute(self._table.delete().where(column("key") == key))
            connection.commit()

        return True

    @override
    def clear(self) -> bool:
        with self._db.connection(self._config.connection) as connection:
            connection.execute(self._table.delete())
            connection.commit()

        return True

    @override
    def lock(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> Lock:
        from expanse.cache.synchronous.locks.database_lock import DatabaseLock

        connection = self._db.connection(self._config.connection)

        return DatabaseLock(
            connection=connection,
            table_name=self._config.locks_table,
            name=name,
            ttl=ttl,
            owner=owner,
            refresh=refresh,
        )

    def _postgres_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.postgresql import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["key"], set_=insert_stmt.excluded
        )

        with self._db.connection(self._config.connection) as connection:
            connection.execute(upsert_stmt)
            connection.commit()

    def _mysql_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.mysql import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_duplicate_key_update(
            data=insert_stmt.inserted.data,
            expiration=insert_stmt.inserted.expiration,
            status="U",
        )

        with self._db.connection(self._config.connection) as connection:
            connection.execute(upsert_stmt)
            connection.commit()

    def _sqlite_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.sqlite import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["key"],
            set_=insert_stmt.excluded,
        )

        with self._db.connection(self._config.connection) as connection:
            connection.execute(upsert_stmt)
            connection.commit()
