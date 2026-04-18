from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from expanse.configuration.config import Config
from expanse.redis.exceptions import MissingRedisPackageError
from expanse.redis.exceptions import UnconfiguredConnectionError


if TYPE_CHECKING:
    from expanse.redis.synchronous.connections.connection import Connection


class RedisManager:
    def __init__(self, config: Config) -> None:
        self._config: Config = config
        self._connections: dict[str, Connection] = {}

    def connection(self, name: str | None = None) -> "Connection":
        """
        Get a Redis connection by name.

        :param name: The name of the connection to retrieve. If None, the default connection will be returned.
        :return: A Redis connection instance.
        """
        if name is None:
            name = self.get_default_connection_name()

        if name in self._connections:
            return self._connections[name]

        connections_configs = self._config.get("redis.connections", {})
        if name not in connections_configs:
            raise UnconfiguredConnectionError(
                f"The Redis connection '{name}' is not configured."
            )

        connection_config = connections_configs[name]

        connection = self._create_connection(connection_config)

        self._connections[name] = connection

        return connection

    def get_default_connection_name(self) -> str:
        return self._config.get("redis.connection", "default")

    def close(self) -> None:
        for connection in self._connections.values():
            connection.close()

    def _create_connection(self, raw_config: dict[str, Any]) -> "Connection":
        from redis.backoff import AbstractBackoff
        from redis.retry import Retry

        from expanse.redis.config.redis import ConstantBackoffConfig
        from expanse.redis.config.redis import GenericBackoffConfig
        from expanse.redis.config.redis import RedisConfig

        config = RedisConfig.model_validate(raw_config)

        try:
            from redis import Redis
            from redis import RedisCluster
        except ImportError:
            raise MissingRedisPackageError(
                "The 'redis' package is required to use Redis connections. "
                "Install expanse with the 'redis' extra to include the package or add 'redis' to your project dependencies."
            )

        retry: Retry
        if config.backoff is None:
            from redis.backoff import NoBackoff

            retry = Retry(backoff=NoBackoff(), retries=config.max_retries)
        else:
            backoff_config = config.backoff.root
            backoff: AbstractBackoff
            match backoff_config:
                case ConstantBackoffConfig():
                    from redis.backoff import ConstantBackoff

                    backoff = ConstantBackoff(backoff_config.backoff)
                case GenericBackoffConfig():
                    match backoff_config.strategy:
                        case "exponential":
                            from redis.backoff import ExponentialBackoff

                            backoff = ExponentialBackoff(
                                base=backoff_config.base,
                                cap=backoff_config.cap,
                            )
                        case "full_jitter":
                            from redis.backoff import FullJitterBackoff

                            backoff = FullJitterBackoff(
                                base=backoff_config.base,
                                cap=backoff_config.cap,
                            )
                        case "equal_jitter":
                            from redis.backoff import EqualJitterBackoff

                            backoff = EqualJitterBackoff(
                                base=backoff_config.base,
                                cap=backoff_config.cap,
                            )
                        case "decorrelated_jitter":
                            from redis.backoff import DecorrelatedJitterBackoff

                            backoff = DecorrelatedJitterBackoff(
                                base=backoff_config.base,
                                cap=backoff_config.cap,
                            )
                        case "exponential_with_jitter":
                            from redis.backoff import ExponentialWithJitterBackoff

                            backoff = ExponentialWithJitterBackoff(
                                base=backoff_config.base,
                                cap=backoff_config.cap,
                            )

            retry = Retry(backoff=backoff, retries=config.max_retries)

        if config.cluster:
            return cast(
                "Connection",
                RedisCluster.from_url(
                    str(config.url), retry=retry, decode_responses=True
                ),
            )

        return cast(
            "Connection",
            Redis.from_url(str(config.url), retry=retry, decode_responses=True),
        )
