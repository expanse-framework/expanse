from typing import ClassVar

from cleo.helpers import option
from cleo.io.inputs.argument import Argument
from cleo.io.inputs.option import Option

from expanse.common.database.migration.migrator import Migrator
from expanse.database.console.command import MigrationCommand


class DbRollbackCommand(MigrationCommand):
    name: str = "db rollback"

    description: str = "Rollback the last database migration."

    arguments: ClassVar[list[Argument]] = []
    options: ClassVar[list[Option]] = [
        option("step", None, "The number of migrations to revert.", flag=False),
    ]

    help: str = """Rollback the last database migration.

A revision can be provided to rollback to a specific revision.

<info>db rollback my-revision</info>

Alternatively, a negative integer can be provided to rollback a specific number of revisions. For instance:

<info>db rollback -2</info>

This will rollback the last two migrations.
"""

    def handle(self, migrator: Migrator) -> int:
        self.line("")

        revision = "-1"
        if self.option("step"):
            revision = f'-{self.option("step").removeprefix("-")}'

        migrator.rollback(revision=revision, io=self._io)

        return 0
