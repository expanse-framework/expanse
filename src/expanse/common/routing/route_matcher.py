import math
import re
import typing
import urllib.parse
import uuid

from dataclasses import dataclass
from re import Pattern

from expanse.asynchronous.http.request import Request as ASGIRequest
from expanse.common.http.url_path import URLPath
from expanse.common.routing.exceptions import NotEnoughURLParameters
from expanse.common.routing.route import Match
from expanse.common.routing.route import Route
from expanse.http.request import Request


T = typing.TypeVar("T")


class Convertor(typing.Generic[T]):
    regex: typing.ClassVar[str] = ""

    def convert(self, value: str) -> T:
        raise NotImplementedError()  # pragma: no cover

    def to_string(self, value: T) -> str:
        raise NotImplementedError()  # pragma: no cover


class StringConvertor(Convertor):
    regex = "[^/]+"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        value = str(value)
        assert "/" not in value, "May not contain path separators"
        assert value, "Must not be empty"
        return value


class PathConvertor(Convertor):
    regex = ".*"

    def convert(self, value: str) -> str:
        return str(value)

    def to_string(self, value: str) -> str:
        return str(value)


class IntegerConvertor(Convertor):
    regex = "[0-9]+"

    def convert(self, value: str) -> int:
        return int(value)

    def to_string(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "Negative integers are not supported"
        return str(value)


class FloatConvertor(Convertor):
    regex = r"[0-9]+(\.[0-9]+)?"

    def convert(self, value: str) -> float:
        return float(value)

    def to_string(self, value: float) -> str:
        value = float(value)
        assert value >= 0.0, "Negative floats are not supported"
        assert not math.isnan(value), "NaN values are not supported"
        assert not math.isinf(value), "Infinite values are not supported"
        return f"{value:0.20f}".rstrip("0").rstrip(".")


class UUIDConvertor(Convertor):
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def convert(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)

    def to_string(self, value: uuid.UUID) -> str:
        return str(value)


@dataclass
class MatchResult:
    result: Match
    format: str
    convertor: Convertor | None

    def convert(self):
        pass


# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class RouteMatcher:
    def __init__(self) -> None:
        self._convertors: dict[str, Convertor] = {
            "str": StringConvertor(),
            "path": PathConvertor(),
            "int": IntegerConvertor(),
            "float": FloatConvertor(),
            "uuid": UUIDConvertor(),
        }
        self._compiled: dict[str, tuple[Pattern, str, dict[str, Convertor]]] = {}

    def match(self, route: Route, request: Request | ASGIRequest) -> Match:
        match request:
            case Request():
                return self._match_from_request(route, request)

        return self._match_from_asgi_request(route, request)

    def compile_path(self, path: str) -> tuple[Pattern, str, dict[str, Convertor]]:
        """
        Given a path string, like: "/{username:str}",
        or a host string, like: "{subdomain}.mydomain.org", return a three-tuple
        of (regex, format, {param_name:convertor}).

        regex:      "/(?P<username>[^/]+)"
        format:     "/{username}"
        convertors: {"username": StringConvertor()}
        """
        if path in self._compiled:
            return self._compiled[path]

        is_host = not path.startswith("/")

        path_regex = "^"
        path_format = ""
        duplicated_params = set()

        idx = 0
        param_convertors = {}
        for match in PARAM_REGEX.finditer(path):
            param_name, convertor_type = match.groups("str")
            convertor_type = convertor_type.lstrip(":")

            if convertor_type not in self._convertors:
                raise ValueError(f"Unknown parameter convertor {convertor_type}.")

            convertor = self._convertors[convertor_type]

            path_regex += re.escape(path[idx : match.start()])
            path_regex += f"(?P<{param_name}>{convertor.regex})"

            path_format += path[idx : match.start()]
            path_format += f"{{{param_name}}}"

            if param_name in param_convertors:
                duplicated_params.add(param_name)

            param_convertors[param_name] = convertor

            idx = match.end()

        if duplicated_params:
            names = ", ".join(sorted(duplicated_params))
            ending = "s" if len(duplicated_params) > 1 else ""
            raise ValueError(f"Duplicated param name{ending} {names} at path {path}")

        if is_host:
            # Align with `Host.matches()` behavior, which ignores port.
            hostname = path[idx:].split(":")[0]
            path_regex += re.escape(hostname) + "$"
        else:
            path_regex += re.escape(path[idx:]) + "$"

        path_format += path[idx:]

        self._compiled[path] = re.compile(path_regex), path_format, param_convertors

        return self._compiled[path]

    def add_convertor(self, key: str, convertor: Convertor) -> None:
        self._convertors[key] = convertor

    def url(self, path: str, /, **parameters) -> URLPath:
        path_regex, path_format, convertors = self.compile_path(path)

        param_names = set(parameters.keys())
        expected_param_names = set(convertors.keys())

        if not expected_param_names.issubset(param_names):
            raise NotEnoughURLParameters(
                f"Not enough parameters for URL {path}: "
                f"missing "
                f"{', '.join(sorted(expected_param_names.difference(param_names)))}"
            )

        for key, value in list(parameters.items()):
            if "{" + key + "}" in path_format:
                convertor = convertors[key]
                value = convertor.to_string(value)
                path_format = path_format.replace("{" + key + "}", value)
                parameters.pop(key)

        if parameters:
            # If we still have parameters, convert them to a query string
            path_format += f"?{urllib.parse.urlencode(parameters)}"

        return URLPath(path_format)

    def _match_from_request(self, route: Route, request: Request) -> Match:
        path_regex, fmt, convertors = self.compile_path(route.path)
        match = path_regex.match(request.url.path)
        if match:
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = convertors[key].convert(value)
            path_params = request.path_params
            path_params.update(matched_params)

            if route.methods and request.method not in route.methods:
                return Match.PARTIAL

            return Match.FULL

        return Match.NONE

    def _match_from_asgi_request(self, route: Route, request: ASGIRequest) -> Match:
        path_regex, fmt, convertors = self.compile_path(route.path)
        match = path_regex.match(request.url.path)
        if match:
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = convertors[key].convert(value)
            path_params = request.path_params
            path_params.update(matched_params)

            if route.methods and request.method not in route.methods:
                return Match.PARTIAL

            return Match.FULL

        return Match.NONE
