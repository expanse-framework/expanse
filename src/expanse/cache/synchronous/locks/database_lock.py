from __future__ import annotations

import time

from typing import TYPE_CHECKING
from typing import override

from sqlalchemy import TableClause
from sqlalchemy import column
from sqlalchemy import or_
from sqlalchemy import table
from sqlalchemy.exc import IntegrityError

from expanse.cache.synchronous.locks.lock import Lock


if TYPE_CHECKING:
    from expanse.database.synchronous.connection import Connection


class DatabaseLock(Lock):
    def __init__(
        self,
        connection: Connection,
        table_name: str,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
        default_ttl: int = 86400,
    ) -> None:
        super().__init__(name, ttl, owner, refresh=refresh)

        self._connection: Connection = connection
        self._table_name: str = table_name
        self._table: TableClause = table(
            self._table_name, column("key"), column("owner"), column("expiration")
        )
        self._default_ttl: int = default_ttl

    @override
    def _do_acquire(self) -> bool:
        try:
            self._connection.execute(
                self._table.insert().values(
                    key=self._name,
                    owner=self._owner,
                    expiration=self._get_expiration_timestamp(),
                )
            )
            self._connection.commit()

            return True
        except IntegrityError:
            self._connection.rollback()

            result = self._connection.execute(
                self._table.update()
                .where(
                    self._table.c.key == self._name,
                    or_(
                        self._table.c.owner == self._owner,
                        self._table.c.expiration < time.time(),
                    ),
                )
                .values(
                    owner=self._owner,
                    expiration=self._get_expiration_timestamp(),
                )
            )
            self._connection.commit()

            return result.rowcount > 0

    @override
    def _do_release(self, force: bool = False) -> bool:
        if force:
            result = self._connection.execute(
                self._table.delete().where(self._table.c.key == self._name)
            )
            self._connection.commit()
            self._connection.close()

            return result.rowcount > 0

        result = self._connection.execute(
            self._table.delete().where(
                self._table.c.key == self._name, self._table.c.owner == self._owner
            )
        )
        self._connection.commit()
        self._connection.close()

        return result.rowcount > 0

    @override
    def get_current_owner(self) -> str | None:
        result = self._connection.execute(
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

    @override
    def refresh(self, ttl: int | None = None) -> bool:
        result = self._connection.execute(
            self._table.update()
            .where(
                self._table.c.key == self._name,
                self._table.c.owner == self._owner,
            )
            .values(expiration=self._get_expiration_timestamp(ttl))
        )
        self._connection.commit()

        return result.rowcount > 0

    def _get_expiration_timestamp(self, ttl: int | None = None) -> int:
        ttl = ttl if ttl is not None else self._ttl
        if ttl is None:
            ttl = self._default_ttl

        return int(time.time()) + ttl
