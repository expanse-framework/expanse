from collections.abc import Callable
from collections.abc import MutableMapping
from typing import Literal

from alembic import context

from expanse.database.database_manager import DatabaseManager


config = context.config
db: DatabaseManager = context.config.attributes["db"]
include_name: Callable[
    [
        str | None,
        Literal[
            "schema",
            "table",
            "column",
            "index",
            "unique_constraint",
            "foreign_key_constraint",
        ],
        MutableMapping[
            Literal[
                "schema_name",
                "table_name",
                "schema_qualified_table_name",
            ],
            str | None,
        ],
    ],
    bool,
] = context.config.attributes["include_name"]

target_metadata = config.attributes["target_metadata"]


def run_migrations_offline() -> None:
    engine = db.configure_engine()

    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with db.connection() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
