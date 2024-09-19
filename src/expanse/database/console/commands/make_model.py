from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option
from inflection import camelize
from inflection import pluralize
from inflection import underscore

from expanse.common.stubs.generator import Generator
from expanse.core.application import Application
from expanse.database.console.command import MigrationCommand


if TYPE_CHECKING:
    from pathlib import Path


class MakeModelCommand(MigrationCommand):
    name: str = "make model"

    description = "Create a new model file."

    arguments: ClassVar[list[Argument]] = [argument("name", "The name of the model.")]
    options: ClassVar[list[Option]] = [
        option(
            "table",
            None,
            "The name of table associated with the model. Derived from the model name by default.",
            flag=False,
        )
    ]

    def handle(self, app: Application, generator: Generator) -> int:
        self.line("")

        models_path: Path = app.path("models")
        if not models_path.exists():
            models_path.mkdir()
            models_path.joinpath("__init__.py").touch()

        model_name: str = self.argument("name")
        model_name = camelize(model_name)
        table_name: str = self.option("table") or self._infer_table(model_name)
        module_name = underscore(model_name)

        stub = generator.stub("database/model")

        if models_path.joinpath(f"{module_name}.py").exists():
            self.line(
                f'  - <warning>Model file <c1>{app.path(f"models/{module_name}.py", relative=True)}</c1> already exists.</warning>'
            )

            return 1

        stub.generate_to(
            models_path.joinpath(f"{module_name}.py"),
            {
                "model_name": model_name,
                "table_name": table_name,
            },
        )

        self.line(
            f'  - Generated file: <c1>{app.path(f"models/{module_name}.py", relative=True)}</c1>'
        )

        return 0

    def _infer_table(self, model_name: str) -> str:
        return pluralize(underscore(model_name))
