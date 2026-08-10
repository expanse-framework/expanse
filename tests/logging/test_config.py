from __future__ import annotations

from pathlib import Path

import pytest

from pydantic import ValidationError

from expanse.logging.config import ConsoleConfig
from expanse.logging.config import FileConfig
from expanse.logging.config import GroupConfig
from expanse.logging.config import StreamConfig
from expanse.logging.config import SyslogConfig


def test_stream_config_defaults() -> None:
    config = StreamConfig()

    assert config.driver == "stream"
    assert config.stream == "stderr"
    assert config.level == "INFO"
    assert config.enabled is True


def test_console_config_defaults() -> None:
    config = ConsoleConfig()

    assert config.driver == "console"
    assert config.level == "INFO"
    assert config.enabled is True


def test_file_config_validates_path_type() -> None:
    config = FileConfig(path=Path("/var/log/app.log"))

    assert config.path == Path("/var/log/app.log")


def test_file_config_with_path() -> None:
    config = FileConfig(path=Path("/var/log/app.log"))

    assert config.driver == "file"
    assert config.path == Path("/var/log/app.log")


def test_group_config_defaults() -> None:
    config = GroupConfig()

    assert config.driver == "group"
    assert config.channels == []


def test_group_config_channels_from_list() -> None:
    config = GroupConfig(channels=["console", "file"])

    assert config.channels == ["console", "file"]


def test_group_config_channels_from_comma_separated_string() -> None:
    config = GroupConfig(channels="console, file")  # type: ignore[arg-type]

    assert config.channels == ["console", "file"]


def test_syslog_config_defaults() -> None:
    config = SyslogConfig()

    assert config.driver == "syslog"
    assert config.address == "localhost:514"
    assert config.facility == "user"
    assert config.socket_type is None


def test_syslog_config_with_unix_socket() -> None:
    config = SyslogConfig(address="/dev/log", facility="local0", socket_type="udp")

    assert config.address == "/dev/log"
    assert config.facility == "local0"
    assert config.socket_type == "udp"


def test_syslog_config_rejects_unknown_facility() -> None:
    with pytest.raises(ValidationError):
        SyslogConfig(facility="unknown")  # type: ignore[arg-type]
