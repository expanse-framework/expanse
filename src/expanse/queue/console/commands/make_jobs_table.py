from importlib import import_module
from typing import Literal

from expanse.console.commands.command import Command
from expanse.database.migration.migrator import Migrator


class MakeJobsTableCommand(Command):
    name: str = "make jobs table"
    description: str = "Create a migration for the jobs table."

    async def handle(self, migrator: Migrator) -> int:
        from expanse.queue.models.job import Model

        migrator.config.attributes["include_name"] = self.include_name
        migrator.config.attributes["target_metadata"] = Model.metadata
        migrator.models_loader = self._load_models

        migrator.make("Create jobs table", auto=True, io=self._io)

        return 0

    def _load_models(self) -> None:
        import_module("expanse.queue.models.job")

    def include_name(
        self,
        name: str | None,
        type_: Literal[
            "schema",
            "table",
            "column",
            "index",
            "unique_constraint",
            "foreign_key_constraint",
        ],
        reflected: bool,
    ) -> bool:
        match type_:
            case "table":
                return name == "jobs"
            case _:
                return True
