from collections.abc import AsyncGenerator
from collections.abc import Generator

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.core.application import Application
from expanse.logging.channel import LogChannel
from expanse.logging.context import Context
from expanse.logging.logging_manager import LoggingManager
from expanse.support.service_provider import ServiceProvider


class LoggingServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(LoggingManager, self._create_logging_manager)
        self._container.singleton(LogChannel, self._create_channel)
        self._container.scoped(Context, self._create_context)

    async def boot(self, config: Config, container: Container) -> None:
        logging_routing_config = config.get("logging", {}).get("routing", {})

        if not logging_routing_config:
            return

        # If the logging routing configuration is defined,
        # we need to ensure that the channels are created immediately,
        # so that they can be used in the routing configuration.
        manager = await container.get(LoggingManager)
        for logger_name in logging_routing_config:
            manager.route_base_logger(logger_name)

    async def _create_logging_manager(
        self, app: Application
    ) -> AsyncGenerator[LoggingManager]:
        logger = LoggingManager(app)

        yield logger

        logger.terminate()

    async def _create_channel(
        self, logger: LoggingManager, name: str | None = None
    ) -> LogChannel:
        return logger.channel(name)

    def _create_context(self) -> Generator[Context]:
        from expanse.logging.utils import _set_context

        context = Context()
        _set_context(context)

        yield context

        context.clear()
        _set_context(None)
