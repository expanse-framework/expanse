from __future__ import annotations

from collections.abc import Callable
from typing import Any
from typing import TypeAlias


Endpoint: TypeAlias = Callable[..., Any]
