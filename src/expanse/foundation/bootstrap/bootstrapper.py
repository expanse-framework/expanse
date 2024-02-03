from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol


if TYPE_CHECKING:
    from expanse.foundation.application import Application


class Bootstrapper(Protocol):
    @classmethod
    async def bootstrap(cls, app: Application) -> None:
        ...
