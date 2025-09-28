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


class MakeControllerCommand(Command):
    name: str = "make controller"

    description: str = "Create a new controller file."

    arguments: ClassVar[list[Argument]] = [
        argument("name", "The name of the controller.")
    ]

    async def handle(self, app: Application, generator: Generator) -> int:
        controllers_path: Path = app.path("http/controllers")
        if not controllers_path.exists():
            controllers_path.mkdir(parents=True)
            controllers_path.joinpath("__init__.py").touch()

        controller_name: str = self.argument("name")
        controller_name = camelize(controller_name).removesuffix("Controller")
        module_name = underscore(controller_name)
        controller_name = f"{controller_name}Controller"

        stub = generator.stub("controller")

        if controllers_path.joinpath(f"{module_name}.py").exists():
            self.line(
                f"  - <warning>The middleware file <c1>{app.path(f'http/controllers/{module_name}.py', relative=True)}</c1> already exists.</warning>"
            )

            return 1

        stub.generate_to(
            controllers_path.joinpath(f"{module_name}.py"),
            {"name": controller_name},
        )

        self.line("")
        self.line(
            f"  - Generated file: <c1>{app.path(f'http/controllers/{module_name}.py', relative=True)}</c1>"
        )

        return 0
