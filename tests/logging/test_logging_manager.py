from __future__ import annotations

import logging
import time

from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import MagicMock

import pytest

from expanse.logging.channel import GroupLogChannel
from expanse.logging.channel import SimpleLogChannel
from expanse.logging.exceptions import LogChannelConfigurationError
from expanse.logging.exceptions import UnconfiguredLogChannelError
from expanse.logging.logging_manager import LoggingManager


if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from expanse.core.application import Application


@pytest.fixture()
def manager(app: Application) -> Generator[LoggingManager]:
    app.config["logging"] = {
        "default": "stream",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "INFO",
            },
            "stdout": {
                "driver": "stream",
                "stream": "stdout",
                "level": "DEBUG",
            },
            "console": {
                "driver": "console",
                "level": "DEBUG",
            },
        },
    }
    mgr = LoggingManager(app)

    yield mgr

    mgr.terminate()


def test_channel_returns_default_channel(manager: LoggingManager) -> None:
    channel = manager.channel()

    assert isinstance(channel, SimpleLogChannel)


def test_channel_returns_named_channel(manager: LoggingManager) -> None:
    channel = manager.channel("stdout")

    assert isinstance(channel, SimpleLogChannel)


def test_channel_caches_instances(manager: LoggingManager) -> None:
    channel1 = manager.channel("stream")
    channel2 = manager.channel("stream")

    assert channel1 is channel2


def test_channel_raises_for_undefined_channel(manager: LoggingManager) -> None:
    with pytest.raises(
        UnconfiguredLogChannelError, match="Log channel 'nonexistent' is not defined"
    ):
        manager.channel("nonexistent")


def test_creates_stream_channel_stderr(manager: LoggingManager) -> None:
    channel = manager.channel("stream")

    assert isinstance(channel, SimpleLogChannel)


def test_creates_stream_channel_stdout(manager: LoggingManager) -> None:
    channel = manager.channel("stdout")

    assert isinstance(channel, SimpleLogChannel)


def test_creates_console_channel(manager: LoggingManager) -> None:
    channel = manager.channel("console")

    assert isinstance(channel, SimpleLogChannel)


def test_creates_file_channel(app: Application, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    app.config["logging"] = {
        "default": "file",
        "channels": {
            "file": {
                "driver": "file",
                "path": str(log_file),
                "level": "INFO",
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("file")

    assert isinstance(channel, SimpleLogChannel)

    mgr.terminate()


def test_file_channel_writes_to_file(app: Application, tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    app.config["logging"] = {
        "default": "file",
        "channels": {
            "file": {
                "driver": "file",
                "path": str(log_file),
                "level": "INFO",
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("file")
    channel.info("test message")
    time.sleep(0.1)

    mgr.terminate()

    content = log_file.read_text()
    assert "test message" in content


def test_creates_group_channel(app: Application) -> None:
    app.config["logging"] = {
        "default": "group",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "INFO",
            },
            "console": {
                "driver": "console",
                "level": "DEBUG",
            },
            "group": {
                "driver": "group",
                "channels": ["stream", "console"],
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("group")

    assert isinstance(channel, GroupLogChannel)

    mgr.terminate()


def test_invalid_stream_raises_value_error(app: Application) -> None:
    app.config["logging"] = {
        "default": "bad",
        "channels": {
            "bad": {
                "driver": "stream",
                "stream": "invalid",
                "level": "INFO",
            },
        },
    }
    mgr = LoggingManager(app)

    with pytest.raises(LogChannelConfigurationError, match="Invalid stream"):
        mgr.channel("bad")


def test_terminate_stops_all_channels(manager: LoggingManager) -> None:
    channel1 = manager.channel("stream")
    channel2 = manager.channel("stdout")

    assert isinstance(channel1, SimpleLogChannel)
    assert isinstance(channel2, SimpleLogChannel)

    manager.terminate()

    assert not channel1._started
    assert not channel2._started


def test_convenience_methods_delegate_to_default_channel(
    manager: LoggingManager,
) -> None:
    channel = MagicMock()
    manager._channels["stream"] = channel

    manager.debug("d")
    channel.debug.assert_called_once_with("d")

    manager.info("i")
    channel.info.assert_called_once_with("i")

    manager.warning("w")
    channel.warning.assert_called_once_with("w")

    manager.error("e")
    channel.error.assert_called_once_with("e")

    manager.critical("c")
    channel.critical.assert_called_once_with("c")

    manager.exception("x")
    channel.exception.assert_called_once_with("x")


def test_route_base_logger(app: Application) -> None:
    app.config["logging"] = {
        "default": "stream",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "WARNING",
            },
        },
        "routing": {
            "test.routing.logger": ["stream"],
        },
    }
    mgr = LoggingManager(app)

    channels = mgr.route_base_logger("test.routing.logger")

    assert len(channels) == 1
    assert isinstance(channels[0], SimpleLogChannel)

    # The base logger level is set to the minimum of DEBUG (initial) and channel levels
    base_logger = logging.getLogger("test.routing.logger")
    assert base_logger.level == logging.DEBUG

    mgr.terminate()


def test_route_base_logger_caches_results(app: Application) -> None:
    app.config["logging"] = {
        "default": "stream",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "INFO",
            },
        },
        "routing": {
            "test.cache.logger": ["stream"],
        },
    }
    mgr = LoggingManager(app)

    result1 = mgr.route_base_logger("test.cache.logger")
    result2 = mgr.route_base_logger("test.cache.logger")

    assert result1 is result2

    mgr.terminate()


def test_route_base_logger_raises_for_undefined_routing(
    manager: LoggingManager,
) -> None:
    with pytest.raises(
        UnconfiguredLogChannelError,
        match="Log routing for logger 'unknown' is not defined",
    ):
        manager.route_base_logger("unknown")


def test_creates_structured_stream_channel(app: Application) -> None:
    from expanse.logging.formatters.structured import StructuredFormatter

    app.config["logging"] = {
        "default": "stream",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "INFO",
                "structured": True,
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("stream")

    assert isinstance(channel, SimpleLogChannel)
    handler = channel._listener.handlers[0]
    assert isinstance(handler.formatter, StructuredFormatter)

    mgr.terminate()


def test_creates_structured_file_channel(app: Application, tmp_path: Path) -> None:
    from expanse.logging.formatters.structured import StructuredFormatter

    log_file = tmp_path / "structured.log"
    app.config["logging"] = {
        "default": "file",
        "channels": {
            "file": {
                "driver": "file",
                "path": str(log_file),
                "level": "INFO",
                "structured": True,
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("file")

    assert isinstance(channel, SimpleLogChannel)
    handler = channel._listener.handlers[0]
    assert isinstance(handler.formatter, StructuredFormatter)

    mgr.terminate()


def test_structured_file_channel_writes_json(app: Application, tmp_path: Path) -> None:
    import json

    log_file = tmp_path / "structured.log"
    app.config["logging"] = {
        "default": "file",
        "channels": {
            "file": {
                "driver": "file",
                "path": str(log_file),
                "level": "INFO",
                "structured": True,
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("file")
    channel.info("structured message", extra={"user_id": 99})
    time.sleep(0.1)

    mgr.terminate()

    data = json.loads(log_file.read_text().strip())
    assert data["message"] == "structured message"
    assert data["user_id"] == 99


def test_non_structured_channel_does_not_use_structured_formatter(
    app: Application,
) -> None:
    from expanse.logging.formatters.structured import StructuredFormatter

    app.config["logging"] = {
        "default": "stream",
        "channels": {
            "stream": {
                "driver": "stream",
                "stream": "stderr",
                "level": "INFO",
                "structured": False,
            },
        },
    }
    mgr = LoggingManager(app)

    channel = mgr.channel("stream")

    assert isinstance(channel, SimpleLogChannel)
    handler = channel._listener.handlers[0]
    assert not isinstance(handler.formatter, StructuredFormatter)

    mgr.terminate()


def test_file_channel_with_relative_path(app: Application, tmp_path: Path) -> None:
    app.config["logging"] = {
        "default": "file",
        "channels": {
            "file": {
                "driver": "file",
                "path": "log/app.log",
                "level": "INFO",
            },
        },
    }
    # Override base_path to use tmp_path for the relative path resolution
    original_base_path = app.base_path
    app._base_path = tmp_path
    (tmp_path / "log").mkdir()
    mgr = LoggingManager(app)

    channel = mgr.channel("file")
    channel.info("relative path test")
    time.sleep(0.1)

    mgr.terminate()

    app._base_path = original_base_path

    content = (tmp_path / "log" / "app.log").read_text()
    assert "relative path test" in content


def test_new_drivers_can_be_added(app: Application) -> None:
    def create_custom_handler(
        channel_name: str, raw_config: dict[str, Any]
    ) -> logging.Handler:
        return logging.StreamHandler()

    app.config["logging"] = {
        "default": "custom",
        "channels": {
            "custom": {
                "driver": "custom",
                "level": "INFO",
            },
        },
    }
    mgr = LoggingManager(app)
    mgr.extend("custom", create_custom_handler)

    channel = mgr.channel("custom")

    assert isinstance(channel, SimpleLogChannel)

    mgr.terminate()
