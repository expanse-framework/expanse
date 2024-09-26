from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import MappedAsDataclass


class Model(MappedAsDataclass, DeclarativeBase): ...
