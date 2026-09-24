
from pydantic import BaseModel


class OutboxTransportConfig(BaseModel):
    # The database connection to use
    connection: str | None = None
