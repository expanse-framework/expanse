import re

from collections import defaultdict
from collections.abc import Callable
from collections.abc import Iterator
from inspect import Parameter
from typing import Any
from typing import Literal
from typing import NoReturn
from typing import TypedDict

from expanse.contracts.routing.route_collection import RouteCollection
from expanse.core.http.exceptions import HTTPException
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.exceptions import RoutingException
from expanse.routing.route import Route


class Static(TypedDict):
    routes: dict[str, Route]
    children: dict[str, "Dynamic | Static"]
    param: None
    regex: None
    converter: None
    catch_all: Literal[False]


class Dynamic(TypedDict):
    routes: dict[str, Route]
    children: dict[str, "Dynamic | Static"]
    param: str | None
    regex: re.Pattern | None
    converter: Callable[[str], Any] | None
    catch_all: bool


class Finder(RouteCollection):
    def __init__(self) -> None:
        self._static: defaultdict[str, Static] = defaultdict(
            lambda: {
                "routes": {},
                "children": {},
                "param": None,
                "regex": None,
                "converter": None,
                "catch_all": False,
            }
        )

        self._dynamic: Dynamic = {
            "routes": {},
            "children": {},
            "param": None,
            "regex": None,
            "converter": None,
            "catch_all": False,
        }

        self._routes: dict[str, Route] = {}
        self._anonymous_routes: list[Route] = []

    def add(self, route: Route) -> None:
        for method in sorted(route.methods):
            self.route(method, route.path, route)

    def match(self, request: Request) -> Route | None:
        method = request.method
        path = request.path

        return self._match(request, method, path)

    def find(self, name: str) -> Route | None:
        return self._routes.get(name)

    def route(self, method: str, pattern: str, route: Route) -> None:
        if route.name:
            self._routes[route.name] = route
        else:
            self._anonymous_routes.append(route)

        if "{" not in pattern:
            self._static[pattern]["routes"][method] = route

            return

        node: Dynamic | Static = self._dynamic
        matches: Iterator[re.Match[str]] = re.finditer(
            r"\{([\w*]+):?([^/]*)}|\[|]|[^/\[\]{}]+", pattern
        )

        for match in matches:
            catch_all = False

            if node.get("catch_all"):
                raise RoutingException(
                    "A catch-all parameter must be the last part of the route"
                )

            token = match[0]

            # Leaf
            if token == "[":
                node["routes"][method] = route

                continue

            if token == "]":
                break

            if param := match[1]:
                if param.startswith("*"):
                    param = param[1:]

                    token = token[1:]

                    catch_all = True

                # Dynamic
                if token not in node["children"]:
                    converter: Callable[[str], Any] | None = None
                    if (
                        param in route.signature.parameters
                        and route.signature.parameters[param].annotation
                        and route.signature.parameters[param].annotation
                        is not Parameter.empty
                    ):
                        converter = route.signature.parameters[param].annotation

                    node["children"][token] = {
                        "routes": {},
                        "children": {},
                        "param": param,
                        "regex": re.compile(match[2]) if match[2] else None,
                        "converter": converter,
                        "catch_all": catch_all,
                    }

            elif token not in node["children"]:
                # Static
                node["children"][token] = {
                    "routes": {},
                    "children": {},
                    "param": None,
                    "regex": None,
                    "converter": None,
                    "catch_all": False,
                }

            # Move to next node
            node = node["children"][token]

        node["routes"][method] = route

    def _match(self, request: Request, method: str, path: str) -> Route | None:
        if path in self._static:
            if method not in self._static[path]["routes"]:
                # Find a route that matches all methods
                if "*" in self._static[path]["routes"]:
                    return self._static[path]["routes"]["*"]

                alternative_methods = list(
                    self._static[request.url.path]["routes"].keys()
                )

                return self._find_alternative(request, alternative_methods)

            return self._static[path]["routes"][method]

        params: dict[str, Any] = {}

        node: Dynamic | Static = self._dynamic

        tokens = path.strip("/").split("/")

        while tokens and (token := tokens.pop(0)):
            if node.get("catch_all"):
                assert node["param"] is not None

                params[node["param"]] = "/".join(
                    [params[node["param"]], token, *tokens]
                )

                break

            # Check if there is a static match
            if token in node["children"]:
                node = node["children"][token]

                continue

            # Handle dynamic match
            found = False

            for child in node["children"].values():
                if child.get("param") is None:
                    continue

                assert child["param"] is not None

                if child.get("regex") is None and child.get("converter") is None:
                    params[child["param"]] = token
                    node = child
                    found = True

                    break

                regex = child["regex"]
                converter = child["converter"]

                if regex is not None:
                    if not child["catch_all"] and not re.match(regex, token):
                        continue
                    elif child["catch_all"]:
                        param = "/".join([token, *tokens])
                        if not re.match(regex, param):
                            continue
                        else:
                            params[child["param"]] = param
                            tokens.clear()
                            node = child
                            found = True

                            break

                if converter is not None:
                    try:
                        params[child["param"]] = converter(token)
                    except (ValueError, TypeError):
                        continue
                else:
                    params[child["param"]] = token

                node = child
                found = True

                break

            if not found:
                return None

        if not node["routes"]:
            return None

        if method not in node["routes"]:
            if "*" in node["routes"]:
                request.path_params.update(params)

                return node["routes"]["*"]

            alternative_methods = list(node["routes"].keys())

            return self._find_alternative(request, alternative_methods)

        request.path_params.update(params)

        return node["routes"][method]

    def _find_alternative(
        self, request: Request, alternative_methods: list[str]
    ) -> Route | None:
        match request.method:
            case "HEAD":
                return self._match(request, "GET", request.url.path)

            case _:
                if not alternative_methods:
                    return None

                return self._get_route_for_methods(request, alternative_methods)

    def _get_route_for_methods(
        self, request: Request, methods: list[str]
    ) -> Route | None:
        if request.method == "OPTIONS":

            async def endpoint() -> Response:
                return Response(
                    "", status_code=200, headers={"Allow": ", ".join(methods)}
                )

            return Route("OPTIONS", request.url.path, endpoint)

        self._method_not_allowed(request, methods)

    def _method_not_allowed(self, request: Request, methods: list[str]) -> NoReturn:
        raise HTTPException(
            405,
            f"The method {request.method} is not supported for route {request.url.path}. "
            f"Available methods: {', '.join(methods)}",
            headers={"Allow": ", ".join(methods)},
        )

    def __iter__(self) -> Iterator[Route]:
        return iter(
            sorted(
                list(self._routes.values()) + self._anonymous_routes,
                key=lambda r: r.path,
            )
        )
