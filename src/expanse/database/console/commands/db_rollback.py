from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.database.console.command import MigrationCommand
from expanse.database.migration.migrator import Migrator
from expanse.support._concurrency import run_in_threadpool


class DbRollbackCommand(MigrationCommand):
    name: str = "db rollback"

    description: str = "Rollback the last database migration."

    arguments: ClassVar[list[Argument]] = []
    options: ClassVar[list[Option]] = [
        option("step", None, "The number of migrations to apply.", flag=False),
        option("reset", None, "Rollback all migrations."),
    ]

    help: str = """Rollback the last database migration.

A number of migrations to rollback can be specified with the --step option.

<info>db rollback --step 2</info>

Would rollback the last two migrations.

The --reset option can be used to rollback all migrations.
"""

    async def handle(self, migrator: Migrator) -> int:
        self.line("")

        revision = "-1"
        if self.option("step"):
            revision = f"-{self.option('step').removeprefix('-')}"

        if self.option("reset"):
            revision = "base"

        await run_in_threadpool(migrator.rollback, revision=revision, io=self._io)

        return 0
