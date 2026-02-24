
from collections.abc import AsyncGenerator

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.core.application import Application
from expanse.logging.channel import LogChannel
from expanse.logging.logger import Logger
from expanse.support.service_provider import ServiceProvider


class LoggingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Logger)
        self._container.singleton(LogChannel, self._create_channel)

    async def boot(self, config: Config, container: Container) -> None:
        logging_routing_config = config.get("logging", {}).get("routing", {})

        if not logging_routing_config:
            return

        # If the logging routing configuration is defined, we need to ensure that the channels are created immediately, so that they can be used in the routing configuration.
        logger = await container.get(Logger)
        for logger_name in logging_routing_config.keys():
            logger.route_base_logger(logger_name)

    async def _create_logger(self, app: Application) -> AsyncGenerator[Logger]:
        logger = Logger(app)

        yield logger

        logger.terminate()

    async def _create_channel(
        self, logger: Logger, name: str | None = None
    ) -> LogChannel:
        return logger.channel(name)
