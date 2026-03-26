from typing import ClassVar
from typing import Literal

from cleo.helpers import option
from cleo.io.inputs.option import Option

from expanse.console.commands.command import Command
from expanse.database.migration.migrator import Migrator


class MakeMessagesTableCommand(Command):
    name: str = "make messages table"
    description: str = "Create a migration for the messenger messages table."

    options: ClassVar[list[Option]] = [
        option(
            "table-name",
            description="The name of the messenger messages table.",
            flag=False,
            default="messages",
        )
    ]

    async def handle(self, migrator: Migrator) -> int:
        from datetime import datetime
        from typing import Annotated

        from sqlalchemy import BigInteger
        from sqlalchemy import DateTime
        from sqlalchemy import Identity
        from sqlalchemy import String
        from sqlalchemy import Text
        from sqlalchemy.dialects import sqlite
        from sqlalchemy.orm import DeclarativeBase
        from sqlalchemy.orm import Mapped
        from sqlalchemy.orm import MappedAsDataclass

        from expanse.database.orm import column

        class Model(MappedAsDataclass, DeclarativeBase): ...

        class Message(Model):
            __tablename__ = self.option("table-name")
            id: Mapped[
                Annotated[
                    int,
                    column(
                        BigInteger().with_variant(sqlite.INTEGER(), "sqlite"),
                        Identity(always=True),
                        primary_key=True,
                    ),
                ]
            ] = column()
            body: Mapped[str] = column(Text(), nullable=False)
            headers: Mapped[str] = column(Text(), nullable=False)
            queue_name: Mapped[str] = column(String(255), nullable=False, index=True)
            created_at: Mapped[datetime] = column(
                DateTime(timezone=True), nullable=False
            )
            available_at: Mapped[datetime] = column(
                DateTime(timezone=True), nullable=False, index=True
            )
            delivered_at: Mapped[datetime] = column(
                DateTime(timezone=True), nullable=True, index=True
            )

        migrator.config.attributes["include_name"] = self.include_name
        migrator.config.attributes["target_metadata"] = Model.metadata

        migrator.make(
            f"Create {self.option('table-name')} table", auto=True, io=self._io
        )

        return 0

    def _load_models(self) -> None:
        from expanse.messenger.asynchronous.transports.database.models.message import (
            Message,
        )

        Message.__tablename__ = self.option("table-name")

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
