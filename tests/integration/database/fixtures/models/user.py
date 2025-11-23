from typing import Annotated
from typing import ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped

from expanse.database.orm import column
from expanse.database.orm.model import Model


primary_key = Annotated[int, column(init=False, primary_key=True, autoincrement=True)]


class User(Model):
    __tablename__: str = "users"

    id: Mapped[primary_key] = column(init=False)
    first_name: Mapped[str | None] = column(default=None)
    last_name: Mapped[str | None] = column(default=None)
    email: Mapped[str | None] = column(default=None)

    metadata: ClassVar[MetaData] = MetaData()
