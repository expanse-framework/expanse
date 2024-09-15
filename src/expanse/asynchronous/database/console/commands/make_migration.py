from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.asynchronous.database.console.command import MigrationCommand
from expanse.asynchronous.support._concurrency import run_in_threadpool
from expanse.common.database.migration.migrator import Migrator


class MakeMigrationCommand(MigrationCommand):
    name: str = "make migration"

    description = "Create a new migration file."

    arguments: ClassVar[list[Argument]] = [
        argument("name", "The name of the migration")
    ]
    options: ClassVar[list[Option]] = [
        option("auto", None, "Autogenerate the migration")
    ]

    async def handle(self, migrator: Migrator) -> int:
        self.line("")

        await run_in_threadpool(
            migrator.make,
            message=self.argument("name"),
            auto=self.option("auto"),
            io=self._io,
        )

        return 0
