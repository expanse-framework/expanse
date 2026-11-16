from collections.abc import Callable
from typing import Protocol

from expanse.messenger.envelope import Envelope


class Middleware(Protocol):
    def handle(
        self, envelope: Envelope, next_call: Callable[[Envelope], Envelope], /
    ) -> Envelope: ...
