from typing import ClassVar
from typing import Literal

from cleo.helpers import option
from cleo.io.inputs.option import Option
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.mysql import INTEGER

from expanse.console.commands.command import Command
from expanse.database.migration.migrator import Migrator


class MakeCacheTableCommand(Command):
    name: str = "make cache table"
    description: str = "Create a migration for the cache table."

    options: ClassVar[list[Option]] = [
        option(
            "table-name",
            description="The name of the cache table.",
            flag=False,
            default="cache",
        ),
        option(
            "with-locks-table",
            description="Also create a migration for the locks table.",
            flag=False,
            default="cache_locks",
            value_required=False,
        ),
    ]

    async def handle(self, migrator: Migrator) -> int:
        from typing import Annotated

        from sqlalchemy import String
        from sqlalchemy.orm import DeclarativeBase
        from sqlalchemy.orm import Mapped
        from sqlalchemy.orm import MappedAsDataclass

        from expanse.database.orm import column

        class Model(MappedAsDataclass, DeclarativeBase): ...

        class Cache(Model):
            __tablename__ = self.option("table-name")
            key: Mapped[Annotated[str, column(String(), primary_key=True)]] = column()
            data: Mapped[bytes] = column(LargeBinary(), nullable=False)
            expiration: Mapped[int] = column(
                Integer().with_variant(INTEGER(unsigned=True), "mysql"),
                nullable=True,
                index=True,
            )

        if self._io.input.has_parameter_option("--with-locks-table"):
            cache_locks_table = self.option("with-locks-table") or "cache_locks"
        else:
            cache_locks_table = None

        if cache_locks_table:

            class CacheLock(Model):
                __tablename__ = cache_locks_table
                key: Mapped[Annotated[str, column(String(), primary_key=True)]] = (
                    column()
                )
                owner: Mapped[str] = column(String(), nullable=False)
                expiration: Mapped[int] = column(
                    Integer().with_variant(INTEGER(unsigned=True), "mysql"),
                    nullable=True,
                    index=True,
                )

        migrator.config.attributes["include_name"] = self.include_name
        migrator.config.attributes["target_metadata"] = Model.metadata

        migration_message = f"Create {self.option('table-name')} table"
        if cache_locks_table:
            migration_message += f" and {cache_locks_table} table"

        migrator.make(migration_message, auto=True, io=self._io)

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
                return name == self.option("table-name")
            case _:
                return True
