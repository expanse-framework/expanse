import inspect
import logging
import secrets

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.cache.asynchronous.bus import Bus
from expanse.support._concurrency import run_in_threadpool
from expanse.support._concurrency import should_run_in_threadpool


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class MemoryBus(Bus):
    def __init__(self) -> None:
        self._id = secrets.token_hex(nbytes=16)
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
            "Publishing cache message", extra={"message_type": type(message).__name__}
        )

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
                        "Error while handling message with handler '%s'",
                        handler,
                        extra={"message_type": type(message).__name__},
                    )
                    continue

    @override
    def subscribe(
        self,
        message: type[_T],
        handler: Callable[[_T], None] | Callable[[_T], Awaitable[None]],
    ) -> None:
        self._handlers[message].append(handler)

    @override
    async def close(self) -> None:
        self._handlers.clear()
