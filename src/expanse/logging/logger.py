from typing import Any

from expanse.logging.channel import LogChannel
from expanse.logging.logging_manager import LoggingManager


class Logger:
    def __init__(self, manager: LoggingManager) -> None:
        self._manager: LoggingManager = manager

    def channel(self, name: str | None = None) -> LogChannel:
        return self._manager.channel(name)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().critical(message, *args, **kwargs)

    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None:
        self.channel().exception(message, *args, **kwargs)
