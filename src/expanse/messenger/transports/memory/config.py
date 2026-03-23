from typing import Literal

from expanse.messenger.transports.config import BaseTransportConfig


class MemoryTransportConfig(BaseTransportConfig):
    driver: Literal["memory"] = "memory"
