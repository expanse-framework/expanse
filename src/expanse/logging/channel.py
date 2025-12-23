import logging

from abc import ABC
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
from queue import Queue
from typing import Any
from typing import Self


class PreservingQueueHandler(QueueHandler):
    """
    QueueHandler that preserves exc_info for custom formatting.

    This is mainly useful for the Console formatter that needs the actual
    exception object to format tracebacks properly.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Prepare a record for queuing while preserving exc_info.

        The default QueueHandler.prepare() converts exc_info to a string,
        but we need the actual exception object for custom formatting.
        """
        record = logging.makeLogRecord(record.__dict__)

        exc_info = record.exc_info
        record.exc_info = None

        record = super().prepare(record)

        if exc_info:
            record.exc_info = exc_info

        return record


class LogChannel(ABC):
    def __init__(
        self,
        logger: logging.Logger,
        handlers: list[logging.Handler],
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
