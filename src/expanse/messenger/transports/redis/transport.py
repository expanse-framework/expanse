import json

from collections.abc import AsyncIterator

from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.serializer import Serializer
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.messenger.transports.redis.connection import Connection
from expanse.redis.asynchronous.connections.connection import (
    Connection as RedisConnection,
)


class RedisTransport:
    def __init__(
        self,
        redis_connection: RedisConnection,
        config: RedisTransportConfig,
        serializer: Serializer,
    ) -> None:
        self._connection: Connection = Connection(redis_connection, config)
        self._serializer: Serializer = serializer

    async def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        id = await self._connection.add(
            json.dumps(encoded_envelope["body"]), encoded_envelope["headers"], delay
        )

        return envelope.with_stamps(TransportMessageIdStamp(id))

    async def receive(self) -> AsyncIterator[Envelope]:
        async for message in self._connection.get():
            data = json.loads(message["data"])

            envelope = self._serializer.decode(
                {
                    "body": json.loads(data["body"]),
                    "headers": data["headers"],
                }
            )

            yield envelope.with_stamps(TransportMessageIdStamp(message["id"]))

    async def acknowledge(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            # If, for some reason, the message doesn't have a TransportMessageIdStamp,
            # we cannot acknowledge it, meaning the message is unprocessable.
            # We notify the worker of this by raising an UnrecoverableMessageHandlingError,
            # which will cause the worker to reject the message and stop trying to process it.
            raise UnrecoverableMessageHandlingError(
                "Cannot acknowledge message without TransportMessageIdStamp"
            )

        await self._connection.acknowledge(message_id_stamp.id)

    async def reject(self, envelope: Envelope) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            # If, for some reason, the message doesn't have a TransportMessageIdStamp,
            # we cannot reject it, meaning the message is unprocessable.
            # We notify the worker of this by raising an UnrecoverableMessageHandlingError,
            # which will cause the worker to reject the message and stop trying to process it.
            raise UnrecoverableMessageHandlingError(
                "Cannot reject message without TransportMessageIdStamp"
            )

        await self._connection.reject(message_id_stamp.id)
