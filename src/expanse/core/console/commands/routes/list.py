from typing import TYPE_CHECKING

from expanse.console.commands.command import Command
from expanse.routing.router import Router


if TYPE_CHECKING:
    from expanse.routing.route import Route

METHODS_COLORS: dict[str, str] = {
    "GET": "fg=blue",
    "HEAD": "fg=default;options=dark",
    "POST": "fg=yellow",
    "PUT": "fg=yellow",
    "PATCH": "fg=yellow",
    "DELETE": "fg=red",
    "OPTIONS": "fg=default;options=dark",
}


class RoutesListCommand(Command):
    name: str = "routes list"

    def handle(self, router: Router) -> int:
        routes: list[Route] = []

        max_methods_length = 0

        for route in router.routes:
            max_methods_length = max(
                max_methods_length,
                sum(len(method) for method in route.methods) + len(route.methods) - 1,
            )
            routes.append(route)

        routes.sort(key=lambda route: route.path)

        self.line("")

        for route in routes:
            methods_length = (
                sum(len(method) for method in route.methods) + len(route.methods) - 1
            )
            methods = "|".join(
                f"<{METHODS_COLORS.get(method.upper(), 'fg=default')}>{method}</>"
                for method in route.methods
            )
            line = [
                "  ",
                methods,
                " " * (max_methods_length - methods_length + 2),
                route.path,
            ]

            if route.name:
                line.append(f" <options=dark>({route.name})</>")

            self.line("".join(line))

            if self._io.is_verbose():
                padding = " " * (methods_length + max_methods_length - methods_length)
                endpoint = route.endpoint.__module__ + "." + route.endpoint.__qualname__
                self.line(f"  {padding}  <options=dark>{endpoint}</>")

        return 0
