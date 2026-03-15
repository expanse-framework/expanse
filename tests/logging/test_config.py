from __future__ import annotations

from pathlib import Path

import pytest

from pydantic import ValidationError

from expanse.logging.config import ChannelConfig
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
    assert config.formatter is None


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


def test_channel_config_validates_stream_config() -> None:
    config = ChannelConfig.model_validate({"driver": "stream", "stream": "stdout"})

    assert isinstance(config.root, StreamConfig)
    assert config.root.stream == "stdout"


def test_channel_config_validates_console_config() -> None:
    config = ChannelConfig.model_validate({"driver": "console"})

    assert isinstance(config.root, ConsoleConfig)


def test_channel_config_validates_file_config() -> None:
    config = ChannelConfig.model_validate(
        {"driver": "file", "path": "/var/log/app.log"}
    )

    assert isinstance(config.root, FileConfig)
    assert config.root.path == Path("/var/log/app.log")


def test_channel_config_validates_group_config() -> None:
    config = ChannelConfig.model_validate(
        {"driver": "group", "channels": ["console", "file"]}
    )

    assert isinstance(config.root, GroupConfig)
    assert config.root.channels == ["console", "file"]


def test_channel_config_with_custom_level() -> None:
    config = ChannelConfig.model_validate({"driver": "stream", "level": "DEBUG"})

    assert config.root.level == "DEBUG"


def test_channel_config_with_invalid_level() -> None:
    with pytest.raises(ValidationError):
        ChannelConfig.model_validate({"driver": "stream", "level": "INVALID"})


def test_channel_config_with_disabled() -> None:
    config = ChannelConfig.model_validate({"driver": "stream", "enabled": False})

    assert config.root.enabled is False
