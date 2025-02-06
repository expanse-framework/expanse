import re

from collections import defaultdict
from collections.abc import Iterator
from typing import Any
from typing import Literal
from typing import TypedDict

from expanse.core.http.exceptions import HTTPException
from expanse.routing.route import Route


METHOD = Literal[
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH",
    "*",
]


METHODS: list[METHOD] = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH",
    "*",
]


class Static(TypedDict):
    routes: dict[METHOD, Route]
    children: dict[str, "Dynamic | Static"]


class Dynamic(TypedDict):
    routes: dict[METHOD, Route]
    children: dict[str, "Dynamic | Static"]
    param: str | None
    regex: str | None
    catch_all: bool


class Finder:
    def __init__(self) -> None:
        self._static: dict[str, Static] = defaultdict(
            lambda: {"routes": {}, "children": {}}
        )
        self._dynamic: Dynamic = {
            "routes": {},
            "children": {},
            "param": None,
            "regex": None,
            "catch_all": False,
        }
        self._routes: dict[str, Route] = {}

    def route(self, method: METHOD, pattern: str, route: Route) -> None:
        if route.name:
            self._routes[route.name] = route

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
                raise Exception("CATCH ALL")

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
                    node["children"][token] = {
                        "routes": {},
                        "children": {},
                        "param": param,
                        "regex": match[2] or None,
                        "catch_all": catch_all,
                    }
            elif token not in node["children"]:
                # Static
                node["children"][token] = {"routes": {}, "children": {}}

            # Move to next node
            node = node["children"][token]

        node["routes"][method] = route

    def find(self, method: METHOD, path: str) -> tuple[Route, dict[str, Any]]:
        if path in self._static:
            if method not in self._static[path]["routes"]:
                # Find a route that matches all methods
                if "*" in self._static[path]["routes"]:
                    return self._static[path]["routes"]["*"]

                alternative_methods = list(self._static[path]["routes"].keys())
                if not alternative_methods:
                    raise HTTPException(404, "Not Found")

                raise HTTPException(
                    405,
                    "Method Not Allowed",
                    headers={"Allow": ", ".join(alternative_methods)},
                )

            return self._static[path]["routes"][method], {}

        params = {}
        node = self._dynamic

        tokens = path.strip("/").split("/")

        while tokens and (token := tokens.pop(0)):
            if node.get("catch_all"):
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

                if child.get("regex") is None:
                    params[child["param"]] = token
                    node = child
                    found = True

                    break

                if not re.match(child["regex"], token):
                    continue

                params[child["param"]] = token
                node = child
                found = True

                break

            if not found:
                raise HTTPException(404, "Not Found")

        if not node["routes"]:
            raise HTTPException(404, "Not Found")

        if method not in node["routes"]:
            if "*" in node["routes"]:
                return node["routes"]["*"], params

            alternative_methods = list(self._static[path]["routes"].keys())
            if not alternative_methods:
                raise HTTPException(404, "Not Found")

            raise HTTPException(
                405,
                "Method Not Allowed",
                headers={"Allow": ", ".join(alternative_methods)},
            )

        return node["routes"][method], params

    def find_by_name(self, name: str) -> Route:
        return self._routes[name]
