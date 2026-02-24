import logging
import sys

from typing import Any

from expanse.core.application import Application
from expanse.logging.channel import GroupLogChannel
from expanse.logging.channel import LogChannel
from expanse.logging.channel import SimpleLogChannel
from expanse.logging.config import BaseConfig
from expanse.logging.config import ChannelConfig
from expanse.logging.config import ConsoleConfig
from expanse.logging.config import FileConfig
from expanse.logging.config import GroupConfig
from expanse.logging.config import StreamConfig


class Logger:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._channels: dict[str, LogChannel] = {}
        self._routing: dict[str, list[LogChannel]] = {}
        self._config: dict[str, Any] = self._app.config.get("logging", {})

    def channel(self, name: str | None = None) -> LogChannel:
        channel_name = name or self._config["default"]

        if channel_name in self._channels:
            return self._channels[channel_name]

        if channel_name not in self._config.get("channels", {}):
            raise RuntimeError(f"Log channel '{channel_name}' is not defined.")

        config = ChannelConfig.model_validate(self._config["channels"][channel_name])

        channel = self._create_channel(config, channel_name)

        self._channels[channel_name] = channel

        return self._channels[channel_name]

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.channel().critical(message, *args, **kwargs)

    def exception(
        self, message: str | BaseException, *args: Any, **kwargs: Any
    ) -> None:
        self.channel().exception(message, *args, **kwargs)

    def terminate(self) -> None:
        for channel in self._channels.values():
            channel.stop()

        for channels in self._routing.values():
            for channel in channels:
                channel.stop()

    def route_base_logger(self, logger_name: str) -> list[LogChannel]:
        if logger_name in self._routing:
            return self._routing[logger_name]

        if logger_name not in self._config.get("routing", {}):
            raise RuntimeError(
                f"Log routing for logger '{logger_name}' is not defined."
            )

        channel_names = self._config["routing"][logger_name]
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        minimum_level = logger.level
        configs = {}
        for channel_name in channel_names:
            chanel_config = ChannelConfig.model_validate(
                self._config["channels"][channel_name]
            )
            configs[channel_name] = chanel_config
            minimum_level = min(
                minimum_level, getattr(logging, chanel_config.root.level)
            )

        logger.setLevel(minimum_level)

        for channel_name, chanel_config in configs.items():
            channel = self._create_channel(
                chanel_config, channel_name, base_logger=logger
            )
            self._routing.setdefault(logger_name, []).append(channel)

        return self._routing[logger_name]

    def _create_channel(
        self,
        config: ChannelConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        match config.root:
            case StreamConfig():
                channel = self._create_stream_channel(
                    config.root, channel_name, base_logger=base_logger
                )
            case ConsoleConfig():
                channel = self._create_console_channel(
                    config.root, channel_name, base_logger=base_logger
                )
            case FileConfig():
                channel = self._create_file_channel(
                    config.root, channel_name, base_logger=base_logger
                )
            case GroupConfig():
                channel = self._create_group_channel(config.root)

        return channel

    def _create_stream_channel(
        self,
        config: StreamConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        logger = base_logger or self._create_base_logger(config, channel_name)

        stream = config.stream

        match stream:
            case "stdout":
                handler = logging.StreamHandler(sys.stdout)
            case "stderr":
                handler = logging.StreamHandler(sys.stderr)
            case _:
                raise ValueError(f"Invalid stream [{stream}]")

        handler.setFormatter(
            logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")
        )

        return SimpleLogChannel(logger, [handler]).start()

    def _create_console_channel(
        self,
        config: ConsoleConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        from expanse.logging.formatters.console import ConsoleFormatter

        logger = base_logger or self._create_base_logger(config, channel_name)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ConsoleFormatter())

        return SimpleLogChannel(logger, [handler], preserve_exception_info=True).start()

    def _create_file_channel(
        self,
        config: FileConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        logger = base_logger or self._create_base_logger(config, channel_name)

        path = config.path
        if not path.is_absolute():
            path = self._app.base_path.joinpath(path)

        handler = logging.FileHandler(path)
        handler.setFormatter(
            logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")
        )

        return SimpleLogChannel(logger, [handler]).start()

    def _create_group_channel(self, config: GroupConfig) -> GroupLogChannel:
        channels = [self.channel(channel_name) for channel_name in config.channels]

        return GroupLogChannel(channels)

    def _create_base_logger(
        self, config: BaseConfig, channel_name: str
    ) -> logging.Logger:
        logger_name = f"{self._app.config['app.name'].lower()}.{channel_name}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(config.level)
        logger.propagate = False

        return logger
