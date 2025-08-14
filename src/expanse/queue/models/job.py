from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Identity
from sqlalchemy import Index
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import MappedAsDataclass

from expanse.database.orm import column


primary_key = Annotated[
    int,
    column(
        BigInteger()
        .with_variant(sqlite.INTEGER(), "sqlite")
        .with_variant(mysql.BIGINT(unsigned=True), "mysql"),
        Identity(always=True),
        primary_key=True,
    ),
]
unsigned_small_int = Annotated[
    int,
    column(
        SmallInteger()
        .with_variant(sqlite.INTEGER(), "sqlite")
        .with_variant(mysql.SMALLINT(unsigned=True), "mysql")
    ),
]


class Model(MappedAsDataclass, DeclarativeBase): ...


class Job(Model):
    id: Mapped[primary_key] = column()
    queue: Mapped[str] = column(String(255), nullable=False, index=True)
    payload: Mapped[str] = column(Text(), nullable=False)
    attempts: Mapped[unsigned_small_int] = column(nullable=False)
    reserved_at: Mapped[datetime] = column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime] = column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = column(DateTime(timezone=True), nullable=False)

    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            f"ix_{__tablename__}_queue",
            "queue",
            unique=False,
        ),
    )
