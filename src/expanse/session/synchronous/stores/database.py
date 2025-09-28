from __future__ import annotations

import base64

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple
from typing import cast

from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import column
from sqlalchemy import exists
from sqlalchemy import select
from sqlalchemy import table
from sqlalchemy import text

from expanse.session.synchronous.stores.store import Store


if TYPE_CHECKING:
    from expanse.database.synchronous.database_manager import DatabaseManager
    from expanse.http.request import Request


class SessionRow(NamedTuple):
    id: str
    ip_address: str | None
    user_agent: str | None
    payload: str
    last_activity: datetime


class DatabaseStore(Store):
    def __init__(
        self,
        db: DatabaseManager,
        table_name: str,
        lifetime: int,
        database_name: str | None = None,
    ) -> None:
        self._db = db
        self._table = table(
            table_name,
            column("id", String(length=40)),
            column("ip_address", String()),
            column("user_agent", Text()),
            column("payload", Text()),
            column("last_activity", DateTime(timezone=True)),
        )
        self._lifetime = lifetime
        self._database_name = database_name

    def read(self, session_id: str) -> str:
        with self._db.connection(self._database_name) as connection:
            session: SessionRow | None = cast(
                "SessionRow | None",
                connection.execute(
                    self._table.select().where(column("id") == session_id)
                ).first(),
            )

        if session is None:
            return ""

        if self._is_session_expired(session):
            return ""

        if session.payload:
            return base64.b64decode(session.payload).decode()

        return ""

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        payload = self._get_payload(data, request=request)

        # We will do an upsert for supported dialects. For other dialects, we will
        # do an optimistic insert and handle the exception to do an update.
        engine = self._db.configure_engine(self._database_name)

        match engine.dialect.name:
            case "sqlite":
                self._sqlite_upsert(session_id, payload)
            case "postgresql":
                self._postgres_upsert(session_id, payload)
            case "mysql":
                self._mysql_upsert(session_id, payload)
            case _:
                with self._db.connection(self._database_name) as connection:
                    session_exists = connection.execute(
                        select(exists(text("1")))
                        .select_from(self._table)
                        .where(column("id") == session_id)
                    ).scalar()
                    if session_exists:
                        connection.execute(
                            self._table.update()
                            .where(column("id") == session_id)
                            .values(**payload)
                        )
                    else:
                        connection.execute(
                            self._table.insert().values(**{"id": session_id, **payload})
                        )

                    connection.commit()

    def delete(self, session_id: str) -> None:
        with self._db.connection(self._database_name) as connection:
            connection.execute(self._table.delete().where(column("id") == session_id))
            connection.commit()

    def clear(self) -> int:
        with self._db.connection(self._database_name) as connection:
            result = connection.execute(
                self._table.delete().where(
                    column("last_activity")
                    < datetime.now(UTC) - timedelta(minutes=self._lifetime)
                )
            )
            connection.commit()

            return result.rowcount

    def _is_session_expired(self, session: SessionRow) -> bool:
        last_activity: datetime = session.last_activity

        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=UTC)

        return (datetime.now(UTC) - last_activity).total_seconds() > self._lifetime * 60

    def _get_payload(self, data: str, request: Request | None = None) -> dict[str, Any]:
        payload = {
            "payload": base64.b64encode(data.encode()).decode(),
            "last_activity": datetime.now(UTC),
        }

        if not request:
            return payload

        payload["ip_address"] = request.ip
        payload["user_agent"] = request.headers.get("User-Agent", "")[:500]

        return payload

    def _postgres_upsert(self, session_id: str, payload: dict[str, Any]) -> None:
        from sqlalchemy.dialects.postgresql import insert

        insert_stmt = insert(self._table).values(**{"id": session_id, **payload})
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"], set_=payload
        )

        with self._db.connection(self._database_name) as connection:
            connection.execute(upsert_stmt)
            connection.commit()

    def _mysql_upsert(self, session_id: str, payload: dict[str, Any]) -> None:
        from sqlalchemy.dialects.mysql import insert

        insert_stmt = insert(self._table).values(**{"id": session_id, **payload})
        data = {key: insert_stmt.inserted[key] for key in payload}
        upsert_stmt = insert_stmt.on_duplicate_key_update(**data, status="U")

        with self._db.connection(self._database_name) as connection:
            connection.execute(upsert_stmt)
            connection.commit()

    def _sqlite_upsert(self, session_id: str, payload: dict[str, Any]) -> None:
        from sqlalchemy.dialects.sqlite import insert

        insert_stmt = insert(self._table).values(**{"id": session_id, **payload})
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=payload,
        )

        with self._db.connection(self._database_name) as connection:
            connection.execute(upsert_stmt)
            connection.commit()
