import inspect
import logging

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import TypeVar

from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.support._concurrency import run_in_threadpool
from expanse.support._concurrency import should_run_in_threadpool


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class MemoryBus(Bus):
    def __init__(self) -> None:
        self._handlers: dict[
            type[Any], list[Callable[[Any], None] | Callable[[Any], Awaitable[None]]]
        ] = defaultdict(list)

    async def publish(self, message: Any) -> None:
        logger.debug(f"Publishing message: {type[message]}")

        if type(message) in self._handlers:
            for handler in self._handlers[type(message)]:
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
        self._handlers.clear()
