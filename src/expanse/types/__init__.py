from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import MutableMapping
from typing import Any
from typing import Literal
from typing import NotRequired
from typing import TypedDict


class ASGIVersion(TypedDict):
    """
    ASGI spec version.
    """

    spec_version: str
    version: Literal["3.0"]


class BaseScope(TypedDict):
    """
    Base ASGI scope type.
    """

    asgi: ASGIVersion
    client: tuple[str, int] | None
    extensions: NotRequired[dict[str, dict[object, object]]]
    headers: list[tuple[bytes, bytes]]
    http_version: str
    path: str
    query_string: bytes
    raw_path: bytes
    root_path: str
    scheme: str
    server: tuple[str, int | None] | None


class PartialBaseScope(TypedDict):
    asgi: NotRequired[ASGIVersion]
    client: NotRequired[tuple[str, int] | None]
    extensions: NotRequired[dict[str, dict[object, object]]]
    headers: NotRequired[list[tuple[bytes, bytes]]]
    http_version: NotRequired[str]
    path: NotRequired[str]
    query_string: NotRequired[bytes]
    raw_path: NotRequired[bytes]
    root_path: NotRequired[str]
    scheme: NotRequired[str]
    server: NotRequired[tuple[str, int | None] | None]


class HTTPScope(BaseScope):
    """
    HTTP ASGI scope type.
    """

    method: str
    type: Literal["http"]


class PartialHTTPScope(PartialBaseScope):
    """
    Partial HTTP ASGI scope type.
    """

    method: NotRequired[str]
    type: NotRequired[Literal["http"]]


Scope = HTTPScope
PartialScope = PartialHTTPScope
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
