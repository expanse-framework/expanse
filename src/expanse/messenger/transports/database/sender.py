from typing import TYPE_CHECKING

from expanse.contracts.messenger.asynchronous.sender import Sender as SenderContract
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.database.asynchronous.connection import AsyncConnection
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.messenger.transports.database.connection import insert_message
from expanse.messenger.transports.database.connection import messages_table


if TYPE_CHECKING:
    from sqlalchemy import TableClause
    from sqlalchemy.ext.asyncio import AsyncTransaction


class DatabaseSender(SenderContract):
    """
    Store messages in the database.

    Messages are stored through the given connection, usually the scoped one,
    so that they are part of its current transaction, if any.
    """

    def __init__(
        self,
        config: DatabaseTransportConfig,
        connection: AsyncConnection,
        serializer: SerializerContract,
    ) -> None:
        self._config: DatabaseTransportConfig = config
        self._connection: AsyncConnection = connection
        self._serializer: SerializerContract = serializer
        self._table: TableClause = messages_table(self._config.table_name)

    @property
    def connection(self) -> AsyncConnection:
        return self._connection

    async def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        insert_stmt = insert_message(
            self._table,
            self._config,
            encoded_envelope["body"],
            encoded_envelope["headers"],
            delay,
        )

        # When the connection is already in a transaction, the message is stored
        # as part of it, so that it shares its outcome.
        transaction: AsyncTransaction
        if self._connection.in_transaction():
            transaction = self._connection.begin_nested()
        else:
            transaction = self._connection.begin()

        async with transaction as tx:
            if self._connection.dialect.insert_returning:
                result = await self._connection.execute(
                    insert_stmt.returning(self._table.c.id)
                )
                message_id: int = result.scalar_one()
            else:
                result = await self._connection.execute(insert_stmt)
                message_id = result.lastrowid

            await tx.commit()

        return envelope.with_stamps(TransportMessageIdStamp(message_id))

    async def close(self) -> None:
        pass
