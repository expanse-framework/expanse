from typing import Literal

from expanse.messenger.transports.config import BaseTransportConfig


class DatabaseTransportConfig(BaseTransportConfig):
    driver: Literal["database"] = "database"

    # The database connection to use
    connection: str | None = None

    # Name of the table to use for storing messages.
    table_name: str = "messages"

    # Name of the queue to use for storing messages.
    queue_name: str = "default"

    # Timeout (in seconds) before redelivering messages still in handling state (i.e: delivered_at is not null and message is still in table)
    redelivery_timeout: int = 3600
