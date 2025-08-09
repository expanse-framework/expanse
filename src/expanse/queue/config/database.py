from typing import Literal

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    """
    Configuration for the database connection.
    """

    driver: Literal["database"]
    connection: str | None
    table: str
    queue: str
    retry_after: int = 60
    dispatch_after_commit: bool = False
