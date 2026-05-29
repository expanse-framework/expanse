import asyncio
import inspect
import logging
import pickle

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.redis.asynchronous.connections.connection import Connection
from expanse.support._concurrency import run_in_threadpool
from expanse.support._concurrency import should_run_in_threadpool


if TYPE_CHECKING:
    from redis.asyncio.client import PubSub


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class RedisBus(Bus):
    def __init__(
        self, publisher: Connection, subscriber: Connection, channel: str
    ) -> None:
        self._publisher: Connection = publisher
        self._subscriber: Connection = subscriber
        self._pubsub: PubSub = self._subscriber.pubsub()
        self._channel: str = channel
        self._stop_listening: asyncio.Event = asyncio.Event()
        self._listen_task: asyncio.Task[None] = asyncio.create_task(self._listen())
        self._handlers: dict[
            type[Any], list[Callable[[Any], None] | Callable[[Any], Awaitable[None]]]
        ] = defaultdict(list)

    async def publish(self, message: Any) -> None:
        logger.debug(
            f"Publishing message to channel '{self._channel}': {type[message]}"
        )
        print(await self._publisher.publish(self._channel, pickle.dumps(message).hex()))

    def subscribe(
        self, handler: Callable[[Any], None] | Callable[[Any], Awaitable[None]]
    ) -> None:
        hints = inspect.signature(handler).parameters

        if len(hints) != 1:
            raise ValueError(
                "Handler must have exactly one parameter with a type hint."
            )

        self._handlers[hints[next(iter(hints))].annotation].append(handler)

    async def close(self) -> None:
        print("Closing RedisBus")
        self._stop_listening.set()
        self._listen_task.cancel()

    async def _listen(self) -> None:
        logger.debug(f"Starting to listen for messages on channel '{self._channel}'.")

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
                data = payload["data"]
                assert isinstance(data, str)
                message = pickle.loads(bytes.fromhex(data))
            except Exception:
                logger.exception("Error while deserializing message")
                continue

            handlers = self._handlers.get(type(message), [])
            for handler in handlers:
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(message)
                    elif should_run_in_threadpool(handler):
                        await run_in_threadpool(handler, message)
                    else:
                        handler(message)
                except Exception:
                    logger.exception(
                        "Error while handling message with handler '%s'", handler
                    )
                    continue

            await asyncio.sleep(0)

        logger.debug(f"Stopped listening for messages on channel '{self._channel}'.")
        await self._pubsub.unsubscribe(self._channel)
        await self._pubsub.aclose()
