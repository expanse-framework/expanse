from typing import Annotated

from pydantic import Field
from pydantic import RootModel

from expanse.messenger.transports.memory.config import MemoryTransportConfig
from expanse.messenger.transports.sync.config import SyncTransportConfig


class TransportConfig(RootModel[SyncTransportConfig | MemoryTransportConfig]):
    root: Annotated[
        SyncTransportConfig | MemoryTransportConfig,
        Field(discriminator="driver"),
    ]
