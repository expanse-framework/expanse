import asyncio
import inspect
import logging
import pickle
import secrets

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.redis.asynchronous.connections.connection import Connection
from expanse.support._concurrency import should_run_as_async
from expanse.support._concurrency import sync_to_async


if TYPE_CHECKING:
    from redis.asyncio.client import PubSub


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
        self._stop_listening: asyncio.Event = asyncio.Event()
        self._listen_task: asyncio.Task[None] = asyncio.create_task(self._listen())
        self._handlers: dict[
            type[Any], list[Callable[[Any], None] | Callable[[Any], Awaitable[None]]]
        ] = defaultdict(list)

    @property
    @override
    def id(self) -> str:
        return self._id

    @override
    async def publish(self, message: Any) -> None:
        logger.debug(
            "Publishing cache message",
            extra={"channel": self._channel, "message_type": type(message).__name__},
        )
        await self._publisher.publish(
            self._channel,
            message=pickle.dumps({"message": message, "bus_id": self._id}).hex(),
        )

    @override
    def subscribe(
        self,
        message: type[_T],
        handler: Callable[[_T], None] | Callable[[_T], Awaitable[None]],
    ) -> None:
        self._handlers[message].append(handler)

    @override
    async def close(self) -> None:
        self._stop_listening.set()
        self._listen_task.cancel()

    async def _listen(self) -> None:
        logger.debug("Listening for messages", extra={"channel": self._channel})

        await self._pubsub.subscribe(self._channel)

        while not self._stop_listening.is_set():
            try:
                payload = await self._pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
            except asyncio.CancelledError:
                raise
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
                    if inspect.iscoroutinefunction(handler):
                        await handler(message)
                    elif should_run_as_async(handler):
                        await sync_to_async(handler, message)
                    else:
                        handler(message)
                except Exception:
                    logger.exception(
                        "Error while handling message with handler '%s'", handler
                    )
                    continue

            await asyncio.sleep(0)

        logger.debug("Stop listening for messages", extra={"channel": self._channel})
        await self._pubsub.unsubscribe(self._channel)
        await self._pubsub.aclose()
