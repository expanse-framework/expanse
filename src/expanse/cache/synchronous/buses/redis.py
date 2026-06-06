from __future__ import annotations

import logging
import pickle
import secrets
import threading

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.cache.synchronous.bus import Bus


if TYPE_CHECKING:
    from collections.abc import Callable

    from redis.client import PubSub

    from expanse.redis.synchronous.connections.connection import Connection


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class RedisBus(Bus):
    def __init__(
        self, publisher: Connection, subscriber: Connection, channel: str
    ) -> None:
        self._id: str = secrets.token_hex(16)
        self._publisher: Connection = publisher
        self._subscriber: Connection = subscriber
        self._pubsub: PubSub = self._subscriber.pubsub()
        self._channel: str = channel
        self._stop_event: threading.Event = threading.Event()
        self._listen_thread: threading.Thread = threading.Thread(
            target=self._listen, daemon=True
        )
        self._listen_thread.start()
        self._handlers: dict[type[Any], list[Callable[[Any], None]]] = defaultdict(list)

    @property
    @override
    def id(self) -> str:
        return self._id

    @override
    def publish(self, message: Any) -> None:
        logger.debug(
            "Publishing cache message",
            extra={"channel": self._channel, "message_type": type(message).__name__},
        )
        self._publisher.publish(
            self._channel,
            pickle.dumps({"message": message, "bus_id": self._id}).hex(),
        )

    @override
    def subscribe(
        self,
        message: type[_T],
        handler: Callable[[_T], None],
    ) -> None:
        self._handlers[message].append(handler)

    @override
    def close(self) -> None:
        self._stop_event.set()
        self._listen_thread.join(timeout=5.0)
        self._pubsub.unsubscribe(self._channel)
        self._pubsub.close()

    def _listen(self) -> None:
        logger.debug("Listening for messages", extra={"channel": self._channel})

        self._pubsub.subscribe(self._channel)

        while not self._stop_event.is_set():
            try:
                payload = self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
            except Exception:
                logger.exception("Error while listening for messages")
                continue

            if payload is None:
                continue

            try:
                raw_data = payload["data"]
                assert isinstance(raw_data, str)
                message_data = pickle.loads(bytes.fromhex(raw_data))
            except Exception:
                logger.exception("Error while deserializing message")
                continue

            if (
                not isinstance(message_data, dict)
                or "message" not in message_data
                or "bus_id" not in message_data
            ):
                logger.warning("Received invalid message format")
                continue

            if message_data["bus_id"] == self._id:
                logger.debug(
                    "Ignoring message published by this bus instance",
                    extra={"bus_id": self._id},
                )
                continue

            message = message_data["message"]

            handlers = self._handlers.get(type(message), [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception:
                    logger.exception(
                        "Error while handling message with handler '%s'", handler
                    )
                    continue

        logger.debug("Stop listening for messages", extra={"channel": self._channel})
        self._pubsub.unsubscribe(self._channel)
        self._pubsub.close()
