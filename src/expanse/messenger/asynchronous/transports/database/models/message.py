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


primary_key = Annotated[
    int,
    column(
        BigInteger().with_variant(sqlite.INTEGER(), "sqlite"),
        Identity(always=True),
        primary_key=True,
    ),
]


class Model(MappedAsDataclass, DeclarativeBase): ...


class Message(Model):
    id: Mapped[primary_key] = column()
    body: Mapped[str] = column(Text(), nullable=False)
    headers: Mapped[str] = column(Text(), nullable=False)
    queue_name: Mapped[str] = column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = column(
        DateTime(timezone=True), nullable=False, index=True
    )
    delivered_at: Mapped[datetime] = column(
        DateTime(timezone=True), nullable=True, index=True
    )
