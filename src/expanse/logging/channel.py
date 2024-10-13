import logging

from typing import Any


class Channel:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger: logging.Logger = logger

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(message, *args, **kwargs)

    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None:
        self._logger.exception(message, *args, **kwargs)
