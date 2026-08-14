from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Concatenate
from typing import NotRequired
from typing import TypedDict
from typing import TypeVar


Message = Any
MessageT = TypeVar("MessageT")
type MessageHandler[MessageT] = (
    Callable[Concatenate[MessageT, ...], None]
    | Callable[Concatenate[MessageT, ...], Awaitable[None]]
)


class EncodedEnvelopeHeaders(TypedDict):
    stamps: NotRequired[list[bytes]]
    sign: NotRequired[str]


class EncodedEnvelope(TypedDict):
    body: bytes
    headers: EncodedEnvelopeHeaders


type Stamp = Any
StampT = TypeVar("StampT", bound="Stamp")
