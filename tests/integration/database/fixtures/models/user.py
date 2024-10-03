from typing import Annotated

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from expanse.database.orm.model import Model


primary_key = Annotated[
    int, mapped_column(init=False, primary_key=True, autoincrement=True)
]


class User(Model):
    __tablename__: str = "users"

    id: Mapped[primary_key] = mapped_column(init=False)
    first_name: Mapped[str | None] = mapped_column(default=None)
    last_name: Mapped[str | None] = mapped_column(default=None)
    email: Mapped[str | None] = mapped_column(default=None)
