from __future__ import annotations

from unittest.mock import MagicMock

from expanse.logging.logger import Logger


def test_logger_delegates_channel_to_manager() -> None:
    manager = MagicMock()
    logger = Logger(manager)

    logger.channel("custom")

    manager.channel.assert_called_once_with("custom")


def test_logger_delegates_channel_none_to_manager() -> None:
    manager = MagicMock()
    logger = Logger(manager)

    logger.channel()

    manager.channel.assert_called_once_with(None)


def test_logger_debug_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.debug("msg", "arg1", extra={"key": "val"})

    channel.debug.assert_called_once_with("msg", "arg1", extra={"key": "val"})


def test_logger_info_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.info("msg")

    channel.info.assert_called_once_with("msg")


def test_logger_warning_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.warning("msg")

    channel.warning.assert_called_once_with("msg")


def test_logger_error_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.error("msg")

    channel.error.assert_called_once_with("msg")


def test_logger_critical_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.critical("msg")

    channel.critical.assert_called_once_with("msg")


def test_logger_exception_delegates_to_default_channel() -> None:
    channel = MagicMock()
    manager = MagicMock()
    manager.channel.return_value = channel
    logger = Logger(manager)

    logger.exception("msg")

    channel.exception.assert_called_once_with("msg")
