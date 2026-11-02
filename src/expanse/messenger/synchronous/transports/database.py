from typing import TYPE_CHECKING

from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.contracts.messenger.synchronous.transport import (
    Transport as TransportContract,
)
from expanse.database.synchronous.connection import Connection
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.messenger.transports.database.connection import insert_message
from expanse.messenger.transports.database.connection import messages_table


if TYPE_CHECKING:
    from sqlalchemy import Transaction


class DatabaseTransport(TransportContract):
    def __init__(
        self,
        config: DatabaseTransportConfig,
        connection: Connection,
        serializer: SerializerContract,
    ) -> None:
        self._config: DatabaseTransportConfig = config
        self._connection: Connection = connection
        self._serializer: SerializerContract = serializer
        self._table = messages_table(self._config.table_name)

    @property
    def connection(self) -> Connection:
        return self._connection

    def send(self, envelope: Envelope) -> Envelope:
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
        transaction: Transaction
        if self._connection.in_transaction():
            transaction = self._connection.begin_nested()
        else:
            transaction = self._connection.begin()

        with transaction:
            if self._connection.dialect.insert_returning:
                result = self._connection.execute(
                    insert_stmt.returning(self._table.c.id)
                )
                message_id: int = result.scalar_one()
            else:
                message_id = self._connection.execute(insert_stmt).lastrowid

        return envelope.with_stamps(TransportMessageIdStamp(message_id))

    def close(self) -> None:
        pass
