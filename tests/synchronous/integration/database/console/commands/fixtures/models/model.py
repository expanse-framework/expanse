from typing import Annotated

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import MappedAsDataclass
from sqlalchemy.orm import mapped_column


primary_key = Annotated[
    int, mapped_column(init=False, primary_key=True, autoincrement=True)
]


class Model(MappedAsDataclass, DeclarativeBase): ...
