from collections.abc import AsyncGenerator

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
        self._container.register(Context, self._get_context)
        self._container.terminating(self._clear_context)

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

    def _get_context(self) -> Context:
        from expanse.logging.utils import _context

        ctx = _context.get()
        if ctx is not None:
            return ctx

        new_context = Context()
        _context.set(new_context)

        return new_context

    def _clear_context(self) -> None:
        from expanse.logging.utils import _set_context

        _set_context(None)
