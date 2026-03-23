from collections.abc import Callable
from typing import Any
from typing import Concatenate
from typing import TypedDict
from typing import TypeVar


Message = Any
MessageT = TypeVar("MessageT")
type MessageHandler[MessageT] = Callable[Concatenate[MessageT, ...], None]


class Encoded(TypedDict):
    data: str
    type: str


class EncodedEnvelope(TypedDict):
    body: Encoded
    headers: dict[str, Any]


type Stamp = Any
StampT = TypeVar("StampT", bound="Stamp")
