from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.messenger.exceptions import NoDefaultTransportError
from expanse.messenger.exceptions import UnconfiguredTransportError
from expanse.messenger.exceptions import UnsupportedTransportDriverError
from expanse.messenger.registry import Registry
from expanse.messenger.transports.memory.transport import MemoryTransport
from expanse.messenger.transports.sync.transport import SyncTransport


class TransportManager:
    def __init__(
        self, container: Container, config: Config, registry: Registry
    ) -> None:
        self._container: Container = container
        self._registry: Registry = registry
        self._config: Config = config
        self._transports: dict[str, Transport] = {}

    async def transport(self, name: str | None = None) -> Transport:
        if name is None:
            name = self.get_default_transport_name()

        if name in self._transports:
            return self._transports[name]

        transport = await self._create_transport(name)
        self._transports[name] = transport

        return transport

    def get_default_transport_name(self) -> str:
        default_transport: str | None = self._config.get("messenger.transport")
        if default_transport is None:
            raise NoDefaultTransportError("No default transport configured.")

        return default_transport

    async def _create_transport(self, name: str) -> Transport:
        transports: dict[str, Any] = self._config.get("messenger.transports", {})
        if name not in transports:
            raise UnconfiguredTransportError(f"Transport '{name}' is not configured.")

        transport_config = transports[name]

        if "driver" not in transport_config:
            raise UnconfiguredTransportError(
                f"Transport '{name}' is missing a driver configuration."
            )

        match transport_config["driver"]:
            case "sync":
                return self._create_sync_transport(transport_config)
            case "memory":
                return self._create_memory_transport(transport_config)
            case "database":
                return await self._create_database_transport(transport_config)
            case "redis":
                return await self._create_redis_transport(transport_config)
            case _:
                raise UnsupportedTransportDriverError(
                    f"Transport '{name}' has an unsupported driver '{transport_config['driver']}'."
                )

    def _create_sync_transport(self, config: dict[str, Any]) -> Transport:
        return SyncTransport(self._container, self._registry)

    def _create_memory_transport(self, config: dict[str, Any]) -> Transport:
        return MemoryTransport()

    async def _create_database_transport(self, config: dict[str, Any]) -> Transport:
        from expanse.database.database_manager import AsyncDatabaseManager
        from expanse.messenger.transports.database.config import DatabaseTransportConfig
        from expanse.messenger.transports.database.transport import DatabaseTransport

        return DatabaseTransport(
            DatabaseTransportConfig.model_validate(config),
            await self._container.get(AsyncDatabaseManager),
        )

    async def _create_redis_transport(self, raw_config: dict[str, Any]) -> Transport:
        from expanse.messenger.serializer import Serializer
        from expanse.messenger.transports.redis.config import RedisTransportConfig
        from expanse.messenger.transports.redis.transport import RedisTransport
        from expanse.redis.asynchronous.redis_manager import RedisManager

        config = RedisTransportConfig.model_validate(raw_config)
        redis = await self._container.get(RedisManager)

        return RedisTransport(
            await redis.connection(config.connection), config, Serializer()
        )
