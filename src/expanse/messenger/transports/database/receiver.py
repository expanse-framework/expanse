import base64

from collections.abc import AsyncIterator

import msgspec

from sqlalchemy.ext.asyncio import AsyncEngine

from expanse.contracts.messenger.asynchronous.keep_alive_receiver import (
    KeepAliveReceiver as KeepAliveReceiverContract,
)
from expanse.contracts.messenger.serializer import Serializer as SerializerContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.messenger.transports.database.connection import Connection
from expanse.types.messenger import EncodedEnvelopeHeaders


class DatabaseReceiver(KeepAliveReceiverContract):
    """
    Receive messages stored in the database.

    Messages are retrieved, acknowledged and rejected through connections
    of their own, retrieved from the engine, so that they are not tied
    to the transaction of the message being handled.
    """

    def __init__(
        self,
        config: DatabaseTransportConfig,
        engine: AsyncEngine,
        serializer: SerializerContract,
    ) -> None:
        self._config: DatabaseTransportConfig = config
        self._engine: AsyncEngine = engine
        self._connection: Connection = Connection(self._engine, self._config)
        self._serializer: SerializerContract = serializer

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def receive(self) -> AsyncIterator[Envelope]:
        message_row = await self._connection.get()

        if message_row is None:
            return

        try:
            envelope = self._serializer.decode(
                {
                    "body": base64.b64decode(message_row.body.encode()),
                    "headers": msgspec.json.decode(
                        message_row.headers, type=EncodedEnvelopeHeaders
                    ),
                }
            )
        except MessageDecodingFailedError as e:
            yield e.as_envelope().with_stamps(TransportMessageIdStamp(message_row.id))
            return

        yield envelope.with_stamps(TransportMessageIdStamp(message_row.id))

    async def acknowledge(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            # If, for some reason, the message doesn't have a TransportMessageIdStamp,
            # we cannot acknowledge it, meaning the message is unprocessable.
            # We notify the worker of this by raising an UnrecoverableMessageHandlingError,
            # which will cause the worker to reject the message without retrying it,
            # and optionally send it to a failure transport if one is configured.
            raise UnrecoverableMessageHandlingError(
                "Cannot acknowledge an envelope without a TransportMessageIdStamp"
            )

        await self._connection.acknowledge(message_id_stamp.id)

    async def reject(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            # If, for some reason, the message doesn't have a TransportMessageIdStamp,
            # we cannot reject it, meaning the message is unprocessable.
            # We notify the worker of this by raising an UnrecoverableMessageHandlingError,
            # which will cause the worker to reject the message without retrying it,
            # and optionally send it to a failure transport if one is configured.
            raise UnrecoverableMessageHandlingError(
                "Cannot reject an envelope without a TransportMessageIdStamp"
            )

        await self._connection.reject(message_id_stamp.id)

    async def keep_alive(self, envelope: Envelope, duration: int | None = None) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            return

        await self._connection.keep_alive(message_id_stamp.id, duration)

    async def close(self) -> None:
        pass
