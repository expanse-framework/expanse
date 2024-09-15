from typing import TYPE_CHECKING

from expanse.asynchronous.console.commands.command import Command
from expanse.common.database.migration.utils import configure_alembic_loggers


if TYPE_CHECKING:
    from cleo.io.io import IO


class MigrationCommand(Command):
    async def run(self, io: "IO") -> int:
        configure_alembic_loggers(io)

        return await super().run(io)
