import logging

from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from logging.handlers import QueueHandler as BaseQueueHandler
from logging.handlers import QueueListener
from queue import Queue
from typing import Any
from typing import Self


class QueueHandler(BaseQueueHandler):
    """
    A simple extension of logging.handlers.QueueHandler that allows for
    custom preparation of log records before they are enqueued.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Prepare a record for queuing.

        This copies the record to ensure that any modifications
        made by handlers or processors are scoped to a specific channel.
        """
        return logging.makeLogRecord(record.__dict__)


class PreservingQueueHandler(QueueHandler):
    """
    QueueHandler that preserves exc_info for custom formatting.

    This is mainly useful for the Console formatter that needs the actual
    exception object to format tracebacks properly.
    """


class LogChannel(ABC):
    @abstractmethod
    def start(self) -> Self: ...

    @abstractmethod
    def stop(self) -> Self: ...

    @abstractmethod
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def info(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def error(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None: ...


class SimpleLogChannel(LogChannel):
    def __init__(
        self,
        logger: logging.Logger,
        handlers: list[logging.Handler],
        processors: Callable[[logging.LogRecord], logging.LogRecord] | None = None,
        preserve_exception_info: bool = False,
    ) -> None:
        self._logger: logging.Logger = logger

        queue = Queue[logging.LogRecord]()
        queue_handler = (
            PreservingQueueHandler(queue)
            if preserve_exception_info
            else QueueHandler(queue)
        )
        logger.addHandler(queue_handler)

        self._listener: QueueListener = QueueListener(queue, *handlers)

        self._started: bool = False

    def start(self) -> Self:
        if not self._started:
            self._listener.start()
            self._started = True

        return self

    def stop(self) -> Self:
        if self._started:
            self._listener.stop()
            self._started = False

        return self

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


class GroupLogChannel(LogChannel):
    def __init__(self, channels: list[LogChannel]) -> None:
        self._channels: list[LogChannel] = channels

    def start(self) -> Self:
        for channel in self._channels:
            channel.start()
        return self

    def stop(self) -> Self:
        for channel in self._channels:
            channel.stop()

        return self

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        for channel in self._channels:
            channel.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        for channel in self._channels:
            channel.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        for channel in self._channels:
            channel.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        for channel in self._channels:
            channel.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        for channel in self._channels:
            channel.critical(message, *args, **kwargs)

    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None:
        for channel in self._channels:
            channel.exception(message, *args, **kwargs)
