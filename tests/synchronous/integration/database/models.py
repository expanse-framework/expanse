from typing import Annotated

from sqlalchemy import BigInteger
from sqlalchemy import Identity
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import MappedAsDataclass

from expanse.common.database.orm import column


primary_key = Annotated[
    int,
    column(
        BigInteger().with_variant(sqlite.INTEGER(), "sqlite"),
        Identity(always=True),
        primary_key=True,
    ),
]


class Model(MappedAsDataclass, DeclarativeBase): ...


class User(Model):
    __tablename__: str = "users"

    id: Mapped[primary_key] = column()
    first_name: Mapped[str] = column()
    last_name: Mapped[str | None] = column(default=None)
    email: Mapped[str] = column()
