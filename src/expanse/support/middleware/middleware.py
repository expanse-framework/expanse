from collections.abc import Awaitable
from collections.abc import Callable
from typing import Protocol


class Middleware[I, O](Protocol):
    async def handle(
        self, input: I, next_call: Callable[[I], Awaitable[O]], /
    ) -> O: ...
