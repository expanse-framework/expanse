import re

from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlencode

from expanse.contracts.routing.router import Router
from expanse.http.request import Request
from expanse.http.url import URL
from expanse.routing.exceptions import InvalidURLParameter
from expanse.routing.exceptions import NotEnoughURLParameters


if TYPE_CHECKING:
    from collections.abc import Iterator


class URLGenerator:
    def __init__(self, router: Router, request: Request) -> None:
        self._router: Router = router
        self._request: Request = request

    def to(
        self,
        path: str,
        parameters: dict[str, Any] | None = None,
        secure: bool | None = None,
    ) -> str:
        # If the URL is already valid, there is nothing to do, and we return it directly.
        if self._is_valid_url(path):
            return path

        parameters = parameters or {}
        url_path = self._compute_path(path, parameters)

        url = self._request.url

        if secure is not None:
            url = url.replace(scheme="https" if secure else "http")

        return str(url.replace(path=url_path))

    def to_route(
        self,
        name: str,
        parameters: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> str:
        parameters = parameters or {}
        # If the URL is already valid, there is nothing to do, and we return it directly.
        route = self._router.routes.find(name)

        if route is None:
            raise ValueError(f"Route [{name}] is not defined")

        assert route is not None

        url = self._compute_path(route.path, parameters)

        if absolute:
            return str(
                URL(url).replace(
                    scheme=self._request.scheme, netloc=self._request.http_host
                )
            )

        return str(url)

    def _format_parameters(self, parameters: dict[str, Any] | None) -> str:
        if parameters is None:
            return ""

        return urlencode(parameters)

    def _is_valid_url(self, path: str) -> bool:
        return re.match(r"^(#|//|https?://|(mailto|tel|sms):)", path) is not None

    def _compute_path(self, path: str, parameters: dict[str, Any]) -> str:
        matches: Iterator[re.Match[str]] = re.finditer(
            r"\{([\w*]+):?([^/]*)}|\[|]|[^/\[\]{}]+", path
        )

        if not matches and parameters:
            raise ValueError(f"Route [{path}] does not expect parameters")

        if not matches:
            return path

        expected: set[str] = set()
        substitutions: dict[str, str] = {}

        for match in matches:
            if match.group(0) in ("[", "]"):
                continue

            raw_name = match.group(1)
            if raw_name is None:
                continue

            name = raw_name

            if name.startswith("*"):
                name = name[1:]

            expected.add(raw_name)

            if name not in parameters:
                continue

            regex = match.group(2)
            if regex and not re.match(regex, str(parameters[name])):
                raise InvalidURLParameter(
                    f"Parameter [{name}] does not match the regex [{regex}]"
                )

            if name.startswith("*"):
                name = name[1:]

            if regex:
                path = path.replace(f"{{{raw_name}:{regex}}}", f"{{{raw_name}}}", 1)

            substitutions[raw_name] = parameters.pop(name)

        if not expected.issubset(set(substitutions.keys())):
            missing = ", ".join(sorted(expected.difference(set(substitutions.keys()))))

            raise NotEnoughURLParameters(
                f"Not enough parameters for URL {path}: missing {missing}"
            )

        path = path.format(**substitutions)

        if parameters:
            return f"{path}?{self._format_parameters(parameters)}"

        return path
