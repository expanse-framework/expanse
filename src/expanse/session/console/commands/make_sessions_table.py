from importlib import import_module
from typing import Literal

from expanse.console.commands.command import Command
from expanse.database.migration.migrator import Migrator
from expanse.session.session_manager import SessionManager


class MakeSessionsTableCommand(Command):
    name: str = "make sessions table"
    description: str = "Create a migration for the sessions table."

    async def handle(self, manager: SessionManager, migrator: Migrator) -> int:
        from expanse.session.models.session import Model

        migrator.config.attributes["include_name"] = self.include_name
        migrator.config.attributes["target_metadata"] = Model.metadata
        migrator.models_loader = self._load_models

        migrator.make("Create sessions table", auto=True, io=self._io)

        return 0

    def _load_models(self) -> None:
        import_module("expanse.session.models.session")

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
