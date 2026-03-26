import json

from expanse.database.asynchronous.database_manager import AsyncDatabaseManager
from expanse.messenger.asynchronous.transports.database.connection import Connection
from expanse.messenger.envelope import Envelope
from expanse.messenger.serializer import Serializer
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig


class DatabaseTransport:
    def __init__(
        self,
        config: DatabaseTransportConfig,
        db: AsyncDatabaseManager,
        serializer: Serializer | None = None,
    ) -> None:
        self._config: DatabaseTransportConfig = config
        self._db: AsyncDatabaseManager = db
        self._connection: Connection = Connection(self._db, self._config)
        self._serializer: Serializer = serializer or Serializer()

    async def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        message_row_id = await self._connection.send(
            body=json.dumps(encoded_envelope["body"]),
            headers=encoded_envelope["headers"],
            delay=delay,
        )

        return envelope.with_stamps(TransportMessageIdStamp(message_row_id))

    async def receive(self) -> Envelope | None:
        message_row = await self._connection.get()

        if message_row is None:
            return None

        envelope = self._serializer.decode(
            {
                "body": json.loads(message_row.body),
                "headers": json.loads(message_row.headers),
            }
        )

        return envelope.with_stamps(TransportMessageIdStamp(message_row.id))

    async def acknowledge(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Cannot acknowledge an envelope without a TransportMessageIdStamp"
            )

        await self._connection.acknowledge(message_id_stamp.id)

    async def reject(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            raise ValueError(
                "Cannot reject an envelope without a TransportMessageIdStamp"
            )

        await self._connection.reject(message_id_stamp.id)
