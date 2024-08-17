from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from expanse.core.helpers import _get_container


if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import MutableMapping

    from expanse.http.response import Response
    from expanse.routing.redirect import Redirect
    from expanse.routing.responder import Responder


def abort(
    status_code: int,
    message: str | None = None,
    headers: MutableMapping[str, str] | None = None,
) -> NoReturn:
    respond().abort(status_code, message, headers)


def json(
    content: Any = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
    **kwargs: Any,
) -> Response:
    return respond().json(content, status_code, headers, **kwargs)


def redirect() -> Redirect:
    return respond().redirect()


def respond() -> Responder:
    container = _get_container()

    from expanse.routing.responder import Responder

    return container.make(Responder)


def response(
    content: str = "",
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return respond().html(content, status_code, headers)


def view(
    view: str,
    data: Mapping[str, Any] | None = None,
    status_code: int = 200,
    headers: MutableMapping[str, Any] | None = None,
) -> Response:
    return respond().view(view, data, status_code, headers)
