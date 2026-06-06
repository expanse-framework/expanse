from __future__ import annotations

import logging
import secrets

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar
from typing import override

from expanse.contracts.cache.synchronous.bus import Bus


if TYPE_CHECKING:
    from collections.abc import Callable


_T = TypeVar("_T")

logger = logging.getLogger(__name__)


class MemoryBus(Bus):
    def __init__(self) -> None:
        self._id = secrets.token_hex(nbytes=16)
        self._handlers: dict[type[Any], list[Callable[[Any], None]]] = defaultdict(list)

    @property
    @override
    def id(self) -> str:
        return self._id

    @override
    def publish(self, message: Any) -> None:
        logger.debug(
            "Publishing cache message", extra={"message_type": type(message).__name__}
        )

        if type(message) in self._handlers:
            for handler in self._handlers[type(message)]:
                try:
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
        handler: Callable[[_T], None],
    ) -> None:
        self._handlers[message].append(handler)

    @override
    def close(self) -> None:
        self._handlers.clear()
