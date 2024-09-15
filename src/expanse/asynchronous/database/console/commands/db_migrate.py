from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.asynchronous.database.console.command import MigrationCommand
from expanse.asynchronous.support._concurrency import run_in_threadpool
from expanse.common.database.migration.migrator import Migrator


class DbMigrateCommand(MigrationCommand):
    name: str = "db migrate"

    description = "Upgrade the database to the latest revision."

    arguments: ClassVar[list[Argument]] = []
    options: ClassVar[list[Option]] = [
        option("step", None, "The number of migrations to apply.", flag=False),
        option(
            "dry-run",
            None,
            "Display the SQL queries that would be run, instead of executing them",
        ),
    ]

    help = """
Upgrade the database to the latest revision.

A number of migrations to apply can be specified with the --step option.

<info>db migrate --step 2</info>

This will apply the next two migrations.
"""

    async def handle(self, migrator: Migrator) -> int:
        self.line("")

        dry_run: bool = self.option("dry-run")

        revision = "head"
        if self.option("step"):
            revision = f'+{self.option("step").removeprefix("+")}'

        await run_in_threadpool(
            migrator.migrate,
            revision=revision,
            dry_run=dry_run,
            io=self._io,
        )

        return 0
