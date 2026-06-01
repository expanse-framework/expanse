import logging
import sys

from typing import Any

from expanse.core.application import Application
from expanse.logging.channel import GroupLogChannel
from expanse.logging.channel import LogChannel
from expanse.logging.channel import SimpleLogChannel
from expanse.logging.channel import SyncLogChannel
from expanse.logging.config import BaseConfig
from expanse.logging.config import ConsoleConfig
from expanse.logging.config import FileConfig
from expanse.logging.config import GroupConfig
from expanse.logging.config import StreamConfig
from expanse.logging.exceptions import LogChannelConfigurationError
from expanse.logging.exceptions import UnconfiguredLogChannelError
from expanse.logging.exceptions import UnsupportedLogChannelDriverError


class LoggingManager:
    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(message)s - %(name)s"

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
            raise UnconfiguredLogChannelError(
                f"Log channel '{channel_name}' is not defined."
            )

        config = self._config["channels"][channel_name]

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
            raise UnconfiguredLogChannelError(
                f"Log routing for logger '{logger_name}' is not defined."
            )

        channel_names = self._config["routing"][logger_name]
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        minimum_level = logger.level
        configs = {}
        for channel_name in channel_names:
            channel_config = BaseConfig.model_validate(
                self._config["channels"][channel_name], extra="ignore"
            )
            configs[channel_name] = self._config["channels"][channel_name]
            minimum_level = min(minimum_level, getattr(logging, channel_config.level))

        logger.setLevel(minimum_level)

        for channel_name, channel_config in configs.items():
            channel = self._create_channel(
                channel_config, channel_name, base_logger=logger
            )
            self._routing.setdefault(logger_name, []).append(channel)

        return self._routing[logger_name]

    def _create_channel(
        self,
        config: dict[str, Any],
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:

        driver = config.get("driver")

        if driver is None:
            raise LogChannelConfigurationError(
                f"Log channel '{channel_name}' configuration must include a 'driver' field."
            )

        match driver:
            case "stream":
                channel_config = StreamConfig.model_validate(config)
                channel = self._create_stream_channel(
                    channel_config, channel_name, base_logger=base_logger
                )
            case "console":
                channel_config = ConsoleConfig.model_validate(config)
                channel = self._create_console_channel(
                    channel_config, channel_name, base_logger=base_logger
                )
            case "file":
                channel_config = FileConfig.model_validate(config)
                channel = self._create_file_channel(
                    channel_config, channel_name, base_logger=base_logger
                )
            case "group":
                channel_config = GroupConfig.model_validate(config)
                channel = self._create_group_channel(
                    channel_config, base_logger=base_logger
                )

            case _:
                raise UnsupportedLogChannelDriverError(
                    f"Log channel '{channel_name}' has an unsupported driver '{driver}'."
                )

        return channel

    def _create_stream_channel(
        self,
        config: StreamConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        from expanse.logging.filters.context import ContextFilter

        logger = base_logger or self._create_base_logger(config, channel_name)

        stream = config.stream

        match stream:
            case "stdout":
                handler = logging.StreamHandler(sys.stdout)
            case "stderr":
                handler = logging.StreamHandler(sys.stderr)
            case _:
                raise LogChannelConfigurationError(
                    f"Invalid stream '{stream}' for channel '{channel_name}'."
                )

        fmt = config.format or self.DEFAULT_FORMAT
        if config.structured:
            from expanse.logging.formatters.structured import StructuredFormatter

            handler.setFormatter(StructuredFormatter(fmt=fmt))
        else:
            handler.setFormatter(logging.Formatter(fmt=fmt))

        handler.setLevel(config.level)
        handler.addFilter(ContextFilter())

        if self._config.get("mode", "async") == "sync":
            return SyncLogChannel(logger, [handler]).start()

        return SimpleLogChannel(logger, [handler]).start()

    def _create_console_channel(
        self,
        config: ConsoleConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        from expanse.logging.filters.context import ContextFilter
        from expanse.logging.formatters.console import ConsoleFormatter

        logger = base_logger or self._create_base_logger(config, channel_name)

        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(config.level)
        handler.setFormatter(ConsoleFormatter())
        handler.addFilter(ContextFilter())

        if self._config.get("mode", "async") == "sync":
            return SyncLogChannel(logger, [handler]).start()

        return SimpleLogChannel(logger, [handler], preserve_exception_info=True).start()

    def _create_file_channel(
        self,
        config: FileConfig,
        channel_name: str,
        base_logger: logging.Logger | None = None,
    ) -> LogChannel:
        from expanse.logging.filters.context import ContextFilter

        logger = base_logger or self._create_base_logger(config, channel_name)

        path = config.path
        if not path.is_absolute():
            path = self._app.base_path.joinpath(path)
            path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(path)
        fmt = config.format or self.DEFAULT_FORMAT
        if config.structured:
            from expanse.logging.formatters.structured import StructuredFormatter

            handler.setFormatter(StructuredFormatter(fmt=fmt))
        else:
            handler.setFormatter(logging.Formatter(fmt=fmt))

        handler.setLevel(config.level)
        handler.addFilter(ContextFilter())

        if self._config.get("mode", "async") == "sync":
            return SyncLogChannel(logger, [handler]).start()

        return SimpleLogChannel(logger, [handler]).start()

    def _create_group_channel(
        self, config: GroupConfig, base_logger: logging.Logger | None = None
    ) -> GroupLogChannel:
        if base_logger is not None:
            channels = [
                self._create_channel(
                    self._config.get("channels", {}).get(channel_name, {}),
                    channel_name,
                    base_logger=base_logger,
                )
                for channel_name in config.channels
            ]
        else:
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
