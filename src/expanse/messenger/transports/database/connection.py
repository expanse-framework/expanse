import base64

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import NamedTuple
from typing import cast

import msgspec

from sqlalchemy import column
from sqlalchemy import or_
from sqlalchemy import table

from expanse.database.asynchronous.connection import AsyncConnection
from expanse.messenger.exceptions import TransportError
from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.types.messenger import EncodedEnvelopeHeaders


class MessageRow(NamedTuple):
    id: int
    body: str
    headers: str
    queue_name: str
    created_at: datetime
    available_at: datetime
    delivered_at: datetime | None


class Connection:
    def __init__(
        self, connection: AsyncConnection, config: DatabaseTransportConfig
    ) -> None:
        self._connection: AsyncConnection = connection
        self._config: DatabaseTransportConfig = config
        self._table = table(
            self._config.table_name,
            column("id"),
            column("body"),
            column("headers"),
            column("queue_name"),
            column("created_at"),
            column("available_at"),
            column("delivered_at"),
        )

    async def send(
        self, body: bytes, headers: EncodedEnvelopeHeaders, delay: int = 0
    ) -> int:
        """
        Store a message to the database.

        :param body: The message body to be stored.
        :param headers: The message headers to be stored.
        :param delay: The number of milliseconds to delay the message before it becomes available for processing.
        """
        now = datetime.now(UTC)
        available_at = now + timedelta(milliseconds=delay)

        insert_stmt = self._table.insert().values(
            body=base64.b64encode(body).decode(),
            headers=msgspec.json.encode(headers).decode(),
            queue_name=self._config.queue_name,
            created_at=now,
            available_at=available_at,
        )

        async with self._connection.begin():
            if self._connection.dialect.insert_returning:
                result = await self._connection.execute(
                    insert_stmt.returning(self._table.c.id)
                )
                message_id: int = result.scalar_one()
            else:
                result = await self._connection.execute(insert_stmt)
                message_id = result.lastrowid

            await self._connection.commit()

            return message_id

    async def get(self) -> MessageRow | None:
        """
        Retrieve messages from the database that are available for processing.
        """
        supports_update_returning = self._connection.dialect.update_returning

        if not supports_update_returning:
            # If the database does not support UPDATE ... RETURNING, we will need to execute the update and select in two steps.
            # To ensure atomicity, we will execute both statements within the same transaction and use a SELECT ... FOR UPDATE SKIP LOCKED to claim the message.
            return await self._get_with_select_for_update()

        return await self._get_with_update_returning()

    async def acknowledge(self, message_id: int) -> None:
        """
        Acknowledge a message by deleting it from the database.

        :param message_id: The ID of the message to acknowledge.
        """
        async with self._connection.begin():
            await self._connection.execute(
                self._table.delete().where(self._table.c.id == message_id)
            )
            await self._connection.commit()

    async def reject(self, message_id: int) -> None:
        """
        Reject a message by deleting it from the database.

        :param message_id: The ID of the message to reject.
        """
        async with self._connection.begin():
            await self._connection.execute(
                self._table.delete().where(self._table.c.id == message_id)
            )
            await self._connection.commit()

    async def keep_alive(self, message_id: int, duration: int | None = None) -> None:
        if duration is not None and self._config.redelivery_timeout < duration:
            raise TransportError(
                f"Cannot keep message alive for {duration} seconds, as it exceeds the redelivery timeout of {self._config.redelivery_timeout} seconds"
            )

        now = datetime.now(UTC)

        await self._connection.execute(
            self._table.update()
            .where(self._table.c.id == message_id)
            .values(delivered_at=now)
        )
        await self._connection.commit()

    async def _get_with_update_returning(self) -> MessageRow | None:
        now = datetime.now(UTC)
        redelivery_limit = now - timedelta(seconds=self._config.redelivery_timeout)

        # Use a subquery with FOR UPDATE SKIP LOCKED to atomically find and claim
        # a message in a single UPDATE ... RETURNING statement, preventing multiple
        # workers from processing the same message.
        subquery = (
            self._table.select()
            .with_only_columns(self._table.c.id)
            .where(self._table.c.queue_name == self._config.queue_name)
            .where(self._table.c.available_at <= now)
            .where(
                or_(
                    self._table.c.delivered_at.is_(None),
                    self._table.c.delivered_at < redelivery_limit,
                )
            )
            .order_by(self._table.c.available_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_subquery()

        update_query = (
            self._table.update()
            .where(self._table.c.id == subquery)
            .values(delivered_at=now)
            .returning(
                self._table.c.id,
                self._table.c.body,
                self._table.c.headers,
                self._table.c.queue_name,
                self._table.c.created_at,
                self._table.c.available_at,
                self._table.c.delivered_at,
            )
        )

        async with self._connection.begin():
            result: MessageRow | None = cast(
                "MessageRow | None",
                (await self._connection.execute(update_query)).first(),
            )
            await self._connection.commit()

            return result

    async def _get_with_select_for_update(self) -> MessageRow | None:
        now = datetime.now(UTC)
        redelivery_limit = now - timedelta(seconds=self._config.redelivery_timeout)

        # If the database does not support UPDATE ... RETURNING,
        # we will need to execute the update and select in two steps.
        # To ensure atomicity, we will execute both statements within the same transaction
        # and use a SELECT ... FOR UPDATE SKIP LOCKED to claim the message.
        async with self._connection.begin():
            row_id: int | None = await self._connection.scalar(
                self._table.select()
                .with_only_columns(self._table.c.id)
                .where(self._table.c.queue_name == self._config.queue_name)
                .where(self._table.c.available_at <= now)
                .where(
                    or_(
                        self._table.c.delivered_at.is_(None),
                        self._table.c.delivered_at < redelivery_limit,
                    )
                )
                .order_by(self._table.c.available_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            if row_id is None:
                await self._connection.commit()
                return None

            await self._connection.execute(
                self._table.update()
                .where(self._table.c.id == row_id)
                .values(delivered_at=now)
            )

            result = cast(
                "MessageRow | None",
                (
                    await self._connection.execute(
                        self._table.select().where(self._table.c.id == row_id)
                    )
                ).first(),
            )

            await self._connection.commit()

            return result
