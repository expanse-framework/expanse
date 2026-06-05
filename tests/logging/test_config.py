from __future__ import annotations

from pathlib import Path

from expanse.logging.config import ConsoleConfig
from expanse.logging.config import FileConfig
from expanse.logging.config import GroupConfig
from expanse.logging.config import StreamConfig


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
