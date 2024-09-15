from typing import TYPE_CHECKING

from expanse.common.database.migration.utils import configure_alembic_loggers
from expanse.console.commands.command import Command


if TYPE_CHECKING:
    from cleo.io.io import IO


class MigrationCommand(Command):
    def run(self, io: "IO") -> int:
        configure_alembic_loggers(io)

        return super().run(io)
