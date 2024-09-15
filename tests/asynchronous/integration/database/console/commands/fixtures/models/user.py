from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from tests.asynchronous.integration.database.console.commands.fixtures.models.model import (
    Model,
)
from tests.asynchronous.integration.database.console.commands.fixtures.models.model import (
    primary_key,
)


class User(Model):
    __tablename__: str = "users"

    id: Mapped[primary_key] = mapped_column(init=False)
    first_name: Mapped[str | None] = mapped_column(default=None)
    last_name: Mapped[str | None] = mapped_column(default=None)
    email: Mapped[str | None] = mapped_column(default=None)
