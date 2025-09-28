from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any


type Endpoint = Callable[..., Awaitable[Any]] | Callable[..., Any]
