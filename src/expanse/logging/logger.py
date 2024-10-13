from typing import Any

from expanse.logging.channel import Channel


class Logger:
    def __init__(self, channel: Channel) -> None:
        self._channel = channel

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._channel.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._channel.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._channel.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._channel.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self._channel.critical(message, *args, **kwargs)

    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None:
        self._channel.exception(message, *args, **kwargs)
