from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from expanse.asynchronous.core.helpers import _get_container


if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from expanse.asynchronous.http.response import Response
    from expanse.asynchronous.routing.redirect import Redirect
    from expanse.asynchronous.routing.responder import Responder


async def abort(
    status_code: int,
    message: str | None = None,
    headers: MutableMapping[str, str] | None = None,
) -> NoReturn:
    await (await respond()).abort(status_code, message, headers)


async def json(
    content: Any = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
    **kwargs: Any,
) -> Response:
    return await (await respond()).json(content, status_code, headers, **kwargs)


async def redirect() -> Redirect:
    return (await respond()).redirect()


async def respond() -> Responder:
    container = _get_container()

    from expanse.asynchronous.routing.responder import Responder

    return await container.make(Responder)


async def response(
    content: str = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return await (await respond()).html(content, status_code, headers)


async def view(
    view: str,
    data: MutableMapping[str, Any] | None = None,
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return await (await respond()).view(view, data, status_code, headers)
