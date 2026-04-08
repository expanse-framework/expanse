from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Concatenate
from typing import TypedDict
from typing import TypeVar

from expanse.types.serialization import Encoded


Message = Any
MessageT = TypeVar("MessageT")
type MessageHandler[MessageT] = (
    Callable[Concatenate[MessageT, ...], None]
    | Callable[Concatenate[MessageT, ...], Awaitable[None]]
)


class EncodedEnvelope(TypedDict):
    body: Encoded
    headers: dict[str, Any]


type Stamp = Any
StampT = TypeVar("StampT", bound="Stamp")
