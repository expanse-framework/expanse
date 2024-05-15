from typing import TYPE_CHECKING

from expanse.asynchronous.console.commands.command import Command
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

    async def handle(self, router: Router) -> int:
        routes: list[Route] = []

        for route in router._routes:
            routes.append(route)

        for group in router._groups:
            routes.extend(group.routes)

        routes.sort(key=lambda route: route.path)

        self.line("")

        for route in routes:
            methods = "|".join(
                f"<{METHODS_COLORS.get(method.upper(), 'fg=default')}>{method}</>"
                for method in route.methods
            )
            self.line(f"  {methods}  {route.path}")

        return 0
