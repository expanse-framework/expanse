from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.io.inputs.argument import Argument
from inflection import camelize
from inflection import underscore

from expanse.console.commands.command import Command
from expanse.core.application import Application
from expanse.stubs.generator import Generator


if TYPE_CHECKING:
    from pathlib import Path


class MakeMiddlewareCommand(Command):
    name: str = "make middleware"

    description: str = "Create a new middleware file."

    arguments: ClassVar[list[Argument]] = [
        argument("name", "The name of the middleware.")
    ]

    async def handle(self, app: Application, generator: Generator) -> int:
        middleware_path: Path = app.path("http/middleware")
        if not middleware_path.exists():
            middleware_path.mkdir(parents=True)
            middleware_path.joinpath("__init__.py").touch()

        middleware_name: str = self.argument("name")
        middleware_name = camelize(middleware_name)
        module_name = underscore(middleware_name)

        stub = generator.stub("middleware")

        if middleware_path.joinpath(f"{module_name}.py").exists():
            self.line(
                f"  - <warning>The middleware file <c1>{app.path(f'http/middleware/{module_name}.py', relative=True)}</c1> already exists.</warning>"
            )

            return 1

        stub.generate_to(
            middleware_path.joinpath(f"{module_name}.py"),
            {"name": middleware_name},
        )

        self.line("")
        self.line(
            f"  - Generated file: <c1>{app.path(f'http/middleware/{module_name}.py', relative=True)}</c1>"
        )

        return 0
