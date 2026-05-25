import time

from typing import override

from sqlalchemy import TableClause
from sqlalchemy import column
from sqlalchemy import or_
from sqlalchemy import table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from expanse.cache.asynchronous.locks.lock import Lock


class DatabaseLock(Lock):
    def __init__(
        self,
        connection: AsyncConnection,
        table_name: str,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
        default_ttl: int = 86400,
    ) -> None:
        super().__init__(name, ttl, owner, refresh=refresh)

        self._connection: AsyncConnection = connection
        self._table_name: str = table_name
        self._table: TableClause = table(
            self._table_name, column("key"), column("owner"), column("expiration")
        )
        self._default_ttl: int = default_ttl

    @override
    async def _do_acquire(self) -> bool:
        await self._start_connection()

        try:
            await self._connection.execute(
                self._table.insert().values(
                    key=self._name,
                    owner=self._owner,
                    expiration=self._get_expiration_timestamp(),
                )
            )
            await self._connection.commit()

            return True
        except IntegrityError:
            await self._connection.rollback()

            result = await self._connection.execute(
                self._table.update()
                .where(
                    self._table.c.key == self._name,
                    or_(
                        self._table.c.owner == self._owner,
                        (self._table.c.expiration < time.time()),
                    ),
                )
                .values(
                    owner=self._owner,
                    expiration=self._get_expiration_timestamp(),
                )
            )
            await self._connection.commit()

            return result.rowcount > 0

    @override
    async def _do_release(self, force: bool = False) -> bool:
        if force:
            result = await self._connection.execute(
                self._table.delete().where(self._table.c.key == self._name)
            )
            await self._connection.commit()
            await self._connection.close()

            return result.rowcount > 0

        result = await self._connection.execute(
            self._table.delete().where(
                self._table.c.key == self._name, self._table.c.owner == self._owner
            )
        )

        await self._connection.commit()

        await self._connection.close()

        return result.rowcount > 0

    @override
    async def get_current_owner(self) -> str | None:
        await self._start_connection()

        return await self._do_get_current_owner()

    @override
    async def refresh(self, ttl: int | None = None) -> bool:
        await self._start_connection()

        result = await self._connection.execute(
            self._table.update()
            .where(
                self._table.c.key == self._name,
                self._table.c.owner == self._owner,
            )
            .values(expiration=self._get_expiration_timestamp(ttl))
        )
        await self._connection.commit()

        return result.rowcount > 0

    def _get_expiration_timestamp(self, ttl: int | None = None) -> int:
        ttl = ttl if ttl is not None else self._ttl
        if ttl is None:
            ttl = self._default_ttl

        return int(time.time()) + ttl

    async def _start_connection(self) -> None:
        if not self._connection.sync_connection:
            await self._connection.start()

    async def _do_get_current_owner(self) -> str | None:
        result = await self._connection.execute(
            self._table.select().where(
                self._table.c.key == self._name,
                or_(
                    self._table.c.owner == self._owner,
                    self._table.c.expiration < int(time.time()),
                ),
            )
        )
        row = result.first()
        if row is None:
            return None

        return row[1]
