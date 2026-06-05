from __future__ import annotations

import logging

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from expanse.logging.channel import GroupLogChannel
from expanse.logging.channel import PreservingQueueHandler
from expanse.logging.channel import SimpleLogChannel


if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest import LogCaptureFixture


LOGGER_NAME = "test.channel"


@pytest.fixture()
def channel(caplog: LogCaptureFixture) -> Generator[SimpleLogChannel]:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    ch = SimpleLogChannel(logger, [handler])
    ch.start()

    yield ch

    ch.stop()


def test_simple_channel_start_stop() -> None:
    logger = logging.getLogger("test.channel.start_stop")
    logger.handlers.clear()
    channel = SimpleLogChannel(logger, [logging.StreamHandler()])

    assert not channel._started

    channel.start()
    assert channel._started

    channel.stop()
    assert not channel._started


def test_simple_channel_start_is_idempotent() -> None:
    logger = logging.getLogger("test.channel.idempotent_start")
    logger.handlers.clear()
    channel = SimpleLogChannel(logger, [logging.StreamHandler()])
    channel.start()
    channel.start()

    assert channel._started

    channel.stop()


def test_simple_channel_stop_is_idempotent() -> None:
    logger = logging.getLogger("test.channel.idempotent_stop")
    logger.handlers.clear()
    channel = SimpleLogChannel(logger, [logging.StreamHandler()])
    channel.start()
    channel.stop()
    channel.stop()

    assert not channel._started


def test_simple_channel_debug(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.debug("debug message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "debug message"
    assert caplog.records[0].levelno == logging.DEBUG


def test_simple_channel_info(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.info("info message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "info message"
    assert caplog.records[0].levelno == logging.INFO


def test_simple_channel_warning(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.warning("warning message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "warning message"
    assert caplog.records[0].levelno == logging.WARNING


def test_simple_channel_error(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.error("error message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "error message"
    assert caplog.records[0].levelno == logging.ERROR


def test_simple_channel_critical(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.critical("critical message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "critical message"
    assert caplog.records[0].levelno == logging.CRITICAL


def test_simple_channel_exception(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    try:
        raise ValueError("test error")
    except ValueError:
        channel.exception("exception message")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "exception message"
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].exc_info is not None


def test_simple_channel_with_args(
    channel: SimpleLogChannel, caplog: LogCaptureFixture
) -> None:
    channel.info("hello %s", "world")

    assert len(caplog.records) == 1
    assert caplog.records[0].getMessage() == "hello world"


def test_simple_channel_start_returns_self() -> None:
    logger = logging.getLogger("test.channel.returns_self_start")
    logger.handlers.clear()
    channel = SimpleLogChannel(logger, [logging.StreamHandler()])
    result = channel.start()

    assert result is channel

    channel.stop()


def test_simple_channel_stop_returns_self() -> None:
    logger = logging.getLogger("test.channel.returns_self_stop")
    logger.handlers.clear()
    channel = SimpleLogChannel(logger, [logging.StreamHandler()])
    channel.start()
    result = channel.stop()

    assert result is channel


# GroupLogChannel tests


def test_group_channel_dispatches_to_all_children() -> None:
    mock1 = MagicMock()
    mock2 = MagicMock()
    group = GroupLogChannel([mock1, mock2])

    group.debug("msg")
    mock1.debug.assert_called_once_with("msg")
    mock2.debug.assert_called_once_with("msg")

    group.info("msg")
    mock1.info.assert_called_once_with("msg")
    mock2.info.assert_called_once_with("msg")

    group.warning("msg")
    mock1.warning.assert_called_once_with("msg")
    mock2.warning.assert_called_once_with("msg")

    group.error("msg")
    mock1.error.assert_called_once_with("msg")
    mock2.error.assert_called_once_with("msg")

    group.critical("msg")
    mock1.critical.assert_called_once_with("msg")
    mock2.critical.assert_called_once_with("msg")

    group.exception("msg")
    mock1.exception.assert_called_once_with("msg")
    mock2.exception.assert_called_once_with("msg")


def test_group_channel_start_cascades() -> None:
    mock1 = MagicMock()
    mock2 = MagicMock()
    group = GroupLogChannel([mock1, mock2])

    result = group.start()

    mock1.start.assert_called_once()
    mock2.start.assert_called_once()
    assert result is group


def test_group_channel_stop_cascades() -> None:
    mock1 = MagicMock()
    mock2 = MagicMock()
    group = GroupLogChannel([mock1, mock2])

    result = group.stop()

    mock1.stop.assert_called_once()
    mock2.stop.assert_called_once()
    assert result is group


# PreservingQueueHandler tests


def test_preserving_queue_handler_preserves_exc_info() -> None:
    from queue import Queue

    queue: Queue[logging.LogRecord] = Queue()
    handler = PreservingQueueHandler(queue)

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="error: %s",
        args=("details",),
        exc_info=(ValueError, ValueError("test"), None),
    )

    prepared = handler.prepare(record)

    assert prepared.exc_info is not None
    assert prepared.exc_info[0] is ValueError
    assert prepared.msg == "error: %s"
    assert prepared.args == ("details",)


def test_preserving_queue_handler_without_exc_info() -> None:
    from queue import Queue

    queue: Queue[logging.LogRecord] = Queue()
    handler = PreservingQueueHandler(queue)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )

    prepared = handler.prepare(record)

    assert prepared.exc_info is None
    assert prepared.msg == "hello %s"
    assert prepared.args == ("world",)
