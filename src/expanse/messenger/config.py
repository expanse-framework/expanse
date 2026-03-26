from typing import Annotated

from pydantic import Field
from pydantic import RootModel

from expanse.messenger.transports.database.config import DatabaseTransportConfig
from expanse.messenger.transports.memory.config import MemoryTransportConfig
from expanse.messenger.transports.sync.config import SyncTransportConfig


class TransportConfig(
    RootModel[SyncTransportConfig | MemoryTransportConfig | DatabaseTransportConfig]
):
    root: Annotated[
        SyncTransportConfig | MemoryTransportConfig | DatabaseTransportConfig,
        Field(discriminator="driver"),
    ]
