from expanse.contracts.messenger.asynchronous.sender import Sender
from expanse.contracts.messenger.serializer import Serializer
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.messenger.transports.redis.connection import Connection
from expanse.redis.asynchronous.connections.connection import (
    Connection as RedisConnection,
)


class RedisSender(Sender):
    def __init__(
        self,
        redis_connection: RedisConnection,
        config: RedisTransportConfig,
        serializer: Serializer,
    ) -> None:
        self._config: RedisTransportConfig = config
        self._connection: Connection = Connection(redis_connection, config)
        self._serializer: Serializer = serializer

    async def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        id = await self._connection.add(
            encoded_envelope["body"], encoded_envelope["headers"], delay
        )

        return envelope.with_stamps(TransportMessageIdStamp(id))

    async def close(self) -> None:
        # The connection is owned, and closed, by the Redis manager.
        pass
