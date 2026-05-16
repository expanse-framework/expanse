import pickle
import time

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

from expanse.cache.config.database import DatabaseStoreConfig
from expanse.contracts.cache.asynchronous.store import Store
from expanse.database.asynchronous.database_manager import AsyncDatabaseManager


class DatabaseStore(Store):
    def __init__(self, config: DatabaseStoreConfig, db: AsyncDatabaseManager) -> None:
        self._config: DatabaseStoreConfig = config
        self._db: AsyncDatabaseManager = db
        self._table: TableClause = table(
            self._config.table, column("key"), column("data"), column("expiration")
        )

    @override
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self.set_many({key: value}, ttl)

    @override
    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        now = int(time.time())
        values = [
            {
                "key": key,
                "data": pickle.dumps(value),
                "expiration": now + ttl if ttl is not None else None,
            }
            for key, value in items.items()
        ]

        # We will do an upsert for supported dialects. For other dialects, we will
        # do an optimistic insert and handle the exception to do an update.
        engine = self._db.configure_engine(self._config.connection)

        match engine.dialect.name:
            case "sqlite":
                await self._sqlite_upsert(values)
            case "postgresql":
                await self._postgres_upsert(values)
            case "mysql":
                await self._mysql_upsert(values)
            case _:
                async with self._db.connection(self._config.connection) as connection:
                    for value in values:
                        session_exists = (
                            await connection.execute(
                                select(
                                    exists()
                                    .select_from(self._table)
                                    .where(column("key") == value["key"])
                                )
                            )
                        ).scalar()
                        if session_exists:
                            await connection.execute(
                                self._table.update()
                                .where(column("key") == value["key"])
                                .values(**value)
                            )
                        else:
                            await connection.execute(
                                self._table.insert().values(**value)
                            )

                    await connection.commit()

        return True

    @override
    async def get(self, key: str) -> Any | None:
        return (await self.get_many([key])).get(key)

    async def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        if not keys:
            return {}

        now = int(time.time())
        expired: list[str] = []
        items: dict[str, Any | None] = dict.fromkeys(keys)
        async with self._db.connection(self._config.connection) as connection:
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
            results: CursorResult[tuple[str, bytes | None]] = await connection.execute(
                stmt
            )
            rows = results.fetchall()

            for row in rows:
                key, data = row
                if data is not None:
                    items[key] = pickle.loads(data)
                else:
                    expired.append(key)

            if expired:
                await connection.execute(
                    self._table.delete().where(column("key").in_(expired))
                )

            await connection.commit()

        return items

    async def delete(self, key: str) -> bool:
        async with self._db.connection(self._config.connection) as connection:
            await connection.execute(self._table.delete().where(column("key") == key))
            await connection.commit()

        return True

    async def has(self, key: str) -> bool:
        now = int(time.time())
        async with self._db.connection(self._config.connection) as connection:
            result = await connection.execute(
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

    async def clear(self) -> bool:
        async with self._db.connection(self._config.connection) as connection:
            await connection.execute(self._table.delete())
            await connection.commit()

        return True

    async def _postgres_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.postgresql import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["key"], set_=insert_stmt.excluded
        )

        async with self._db.connection(self._config.connection) as connection:
            await connection.execute(upsert_stmt)
            await connection.commit()

    async def _mysql_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.mysql import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_duplicate_key_update(
            data=insert_stmt.inserted.data,
            expiration=insert_stmt.inserted.expiration,
            status="U",
        )

        async with self._db.connection(self._config.connection) as connection:
            await connection.execute(upsert_stmt)
            await connection.commit()

    async def _sqlite_upsert(self, values: list[dict[str, Any]]) -> None:
        from sqlalchemy.dialects.sqlite import insert

        insert_stmt = insert(self._table).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["key"],
            set_=insert_stmt.excluded,
        )

        async with self._db.connection(self._config.connection) as connection:
            await connection.execute(upsert_stmt)
            await connection.commit()
