from __future__ import annotations

from typing import Any
from typing import Awaitable
from typing import Callable
from typing import MutableMapping


Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
