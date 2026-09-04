from collections.abc import Awaitable
from collections.abc import Callable
from typing import Concatenate


type EventListener[EventT] = (
    Callable[Concatenate[EventT, ...], None]
    | Callable[Concatenate[EventT, ...], Awaitable[None]]
)
