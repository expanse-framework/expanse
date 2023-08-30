from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable
from typing import TypeAlias

from expanse.http.response import Response


Endpoint: TypeAlias = Callable[..., Awaitable[Response]] | Callable[..., Response]
