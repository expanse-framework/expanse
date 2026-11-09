import base64
import secrets
import time

from typing import cast

import msgspec

from redis.exceptions import ResponseError

from expanse.contracts.messenger.serializer import Serializer
from expanse.contracts.messenger.synchronous.sender import Sender as SenderContract
from expanse.messenger.envelope import Envelope
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.transports.redis.config import RedisTransportConfig
from expanse.redis.synchronous.connections.connection import (
    Connection as RedisConnection,
)
from expanse.types.messenger import EncodedEnvelopeHeaders


class RedisSender(SenderContract):
    def __init__(
        self,
        redis_connection: RedisConnection,
        config: RedisTransportConfig,
        serializer: Serializer,
    ) -> None:
        self._connection: RedisConnection = redis_connection
        self._config: RedisTransportConfig = config
        self._queue: str = f"{self._config.stream}__queue"
        self._serializer: Serializer = serializer

    def send(self, envelope: Envelope) -> Envelope:
        encoded_envelope = self._serializer.encode(envelope)
        delay_stamp = envelope.stamp(DelayStamp)
        delay = delay_stamp.delay if delay_stamp is not None else 0

        id = self._add(encoded_envelope["body"], encoded_envelope["headers"], delay)

        return envelope.with_stamps(TransportMessageIdStamp(id))

    def close(self) -> None:
        # The connection is owned, and closed, by the Redis manager.
        pass

    def _add(self, body: bytes, headers: EncodedEnvelopeHeaders, delay: int) -> str:
        """
        Add a message to the Redis stream, or to the delayed messages queue
        if it must be delayed.

        This must store messages exactly as the asynchronous Redis transport does,
        since workers consume them through it.
        """
        if self._config.auto_setup:
            self._setup()

        id: str
        if delay > 0:
            id = base64.b64encode(secrets.token_bytes(9)).decode()
            score = time.time() * 1000 + delay
            if not self._connection.zadd(
                self._queue,
                {
                    msgspec.json.encode(
                        {"body": body, "headers": headers, "uid": id}
                    ): score
                },
                nx=True,
            ):
                raise RuntimeError("Failed to add message to Redis stream")
        else:
            message = msgspec.json.encode({"body": body, "headers": headers})
            id = cast(
                "str",
                self._connection.xadd(
                    self._config.stream,
                    fields={"message": message},
                    maxlen=self._config.max_entries,
                    approximate=True,
                ),
            )
            if not id:
                raise RuntimeError("Failed to add message to Redis stream")

        return id

    def _setup(self) -> None:
        try:
            self._connection.xgroup_create(
                self._config.stream, self._config.group, 0, mkstream=True
            )
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
