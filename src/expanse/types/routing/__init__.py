from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import TypeAlias


Endpoint: TypeAlias = Callable[..., Awaitable[Any]] | Callable[..., Any]
