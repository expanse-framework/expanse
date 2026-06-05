from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextStamp:
    """
    A stamp that indicates that the context has been populated for the message.
    """

    context: Mapping[str, Any]
