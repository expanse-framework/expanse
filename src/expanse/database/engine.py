from typing import cast

from sqlalchemy.engine import Engine as BaseEngine

from expanse.database.connection import Connection


class Engine(BaseEngine):
    _connection_cls = Connection

    def connect(self) -> Connection:
        return cast(Connection, super().connect())
