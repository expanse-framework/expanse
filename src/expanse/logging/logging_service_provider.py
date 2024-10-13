from expanse.logging.channel import Channel
from expanse.logging.logger import Logger
from expanse.logging.logging_manager import LoggingManager
from expanse.support.service_provider import ServiceProvider


class LoggingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(LoggingManager)
        self._container.singleton(Channel, self._create_channel)
        self._container.scoped(Logger, self._create_logger)

    async def _create_channel(
        self, manager: LoggingManager, name: str | None = None
    ) -> Channel:
        return manager.channel(name)

    async def _create_logger(
        self, manager: LoggingManager, name: str | None = None
    ) -> Logger:
        return Logger(manager.channel(name))
