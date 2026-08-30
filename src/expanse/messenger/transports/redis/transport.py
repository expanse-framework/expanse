import logging

from collections.abc import AsyncIterator
from typing import Self
from typing import override

import msgspec

from expanse.contracts.messenger.asynchronous.keep_alive_transport import (
    KeepAliveTransport,
)
from expanse.contracts.messenger.asynchronous.worker_aware_transport import (
    WorkerAwareTransport,
)
from expanse.contracts.messenger.serializer import Serializer
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageDecodingFailedError
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.messenger.transports.redis.connection import Connection
from expanse.redis.asynchronous.connections.connection import (
    Connection as RedisConnection,
)
from expanse.types.messenger import EncodedEnvelope


logger = logging.getLogger(__name__)


class RedisTransport(KeepAliveTransport, WorkerAwareTransport):
    def __init__(
        self,
        redis_connection: RedisConnection,
        config: RedisTransportConfig,
        serializer: Serializer,
    ) -> None:
        self._config: RedisTransportConfig = config
        self._redis_connection: RedisConnection = redis_connection
        self._connection: Connection = Connection(redis_connection, config)
        self._serializer: Serializer = serializer

        logger.debug(
            "Initializing Redis transport",
            extra={"group": config.group, "consumer": config.consumer},
        )

    @override
    def clone_for_worker(self, worker_id: str) -> Self:
        config = self._config.model_copy(
            update={"consumer": f"{self._config.consumer}-{worker_id}"}
        )

        return self.__class__(
            redis_connection=self._redis_connection,
            config=config,
            serializer=self._serializer,
        )

    async def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        id = await self._connection.add(
            encoded_envelope["body"], encoded_envelope["headers"], delay
        )

        return envelope.with_stamps(TransportMessageIdStamp(id))

    async def receive(self) -> AsyncIterator[Envelope]:
        async for message in self._connection.get():
            data = msgspec.json.decode(message["data"], type=EncodedEnvelope)

            try:
                envelope = self._serializer.decode(data)
            except MessageDecodingFailedError as e:
                envelope = e.as_envelope().with_stamps(
                    TransportMessageIdStamp(message["id"])
                )

                yield envelope
                continue

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

    async def keep_alive(self, envelope: Envelope, duration: int | None = None) -> None:
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        if message_id_stamp is None:
            return

        await self._connection.keep_alive(message_id_stamp.id, duration)

    async def close(self) -> None:
        await self._connection.close()
