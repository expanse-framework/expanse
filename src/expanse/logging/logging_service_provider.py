from collections.abc import AsyncGenerator

from expanse.core.application import Application
from expanse.logging.channel import LogChannel
from expanse.logging.logger import Logger
from expanse.support.service_provider import ServiceProvider


class LoggingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(Logger)
        self._container.singleton(LogChannel, self._create_channel)

    async def _create_logger(self, app: Application) -> AsyncGenerator[Logger]:
        logger = Logger(app)

        yield logger

        logger.terminate()

    async def _create_channel(
        self, logger: Logger, name: str | None = None
    ) -> LogChannel:
        return logger.channel(name)
