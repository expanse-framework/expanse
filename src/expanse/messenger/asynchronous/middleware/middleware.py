from collections.abc import Awaitable
from collections.abc import Callable
from typing import Protocol

from expanse.messenger.envelope import Envelope


class Middleware(Protocol):
    async def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Awaitable[Envelope]]
    ) -> Envelope: ...
