from alembic import context

from expanse.common.database.orm.model import Model
from expanse.database.database_manager import DatabaseManager


config = context.config
db: DatabaseManager = context.config.attributes["db"]

target_metadata = Model.metadata


def run_migrations_offline() -> None:
    engine = db.configure_engine()

    context.configure(
        url=engine.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with db.connection() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
