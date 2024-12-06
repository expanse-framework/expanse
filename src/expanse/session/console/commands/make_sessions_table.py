from importlib import import_module
from typing import Literal

from expanse.console.commands.command import Command
from expanse.database.migration.migrator import Migrator


class MakeSessionsTableCommand(Command):
    name: str = "make sessions-table"
    description: str = "Create a migration for the sessions table."

    async def handle(self, migrator: Migrator) -> int:
        migrator.config.attributes["include_name"] = self.include_name

        import_module("expanse.session.models.session")

        self.line("<success>Migration created successfully!</success>")

        return 0

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
                return name == "sessions"
            case _:
                return True
