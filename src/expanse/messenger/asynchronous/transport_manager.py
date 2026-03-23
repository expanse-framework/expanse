from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.messenger.asynchronous.transports.memory.transport import MemoryTransport
from expanse.messenger.asynchronous.transports.sync.transport import SyncTransport
from expanse.messenger.config import TransportConfig
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.registry import Registry
from expanse.messenger.transports.memory.config import MemoryTransportConfig
from expanse.messenger.transports.sync.config import SyncTransportConfig


class TransportManager:
    def __init__(
        self, container: Container, config: Config, registry: Registry
    ) -> None:
        self._container: Container = container
        self._registry: Registry = registry
        self._config: Config = config
        self._transports: dict[str, Transport] = {}

    def transport(self, name: str | None = None) -> Transport:
        if name is None:
            name = self._config.get("messenger.transport")

        if name is None:
            raise NoDefaultTransportError("No default transport configured.")

        if name in self._transports:
            return self._transports[name]

        transport = self._create_transport(name)
        self._transports[name] = transport

        return transport

    def _create_transport(self, name: str) -> Transport:
        transports: dict[str, Any] = self._config.get("messenger.transports", {})
        if name not in transports:
            raise ValueError(f"Transport '{name}' is not configured.")

        transport_config = TransportConfig.model_validate(transports[name]).root

        match transport_config:
            case SyncTransportConfig():
                return self._create_sync_transport(transport_config)
            case MemoryTransportConfig():
                return self._create_memory_transport(transport_config)

    def _create_sync_transport(self, config: SyncTransportConfig) -> Transport:
        return SyncTransport(self._container, self._registry)

    def _create_memory_transport(self, config: MemoryTransportConfig) -> Transport:
        return MemoryTransport()
