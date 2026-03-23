from typing import Literal

from expanse.messenger.transports.config import BaseTransportConfig


class SyncTransportConfig(BaseTransportConfig):
    driver: Literal["sync"] = "sync"
