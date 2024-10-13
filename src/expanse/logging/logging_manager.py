import logging
import sys

from typing import Any

from expanse.core.application import Application
from expanse.logging.channel import Channel
from expanse.logging.config import BaseConfig
from expanse.logging.config import ChannelConfig
from expanse.logging.config import ConsoleConfig
from expanse.logging.config import StreamConfig
from expanse.logging.formatters.console import ConsoleFormatter
from expanse.logging.logger import Logger


class LoggingManager:
    def __init__(self, app: Application) -> None:
        self._app: Application = app
        self._channels: dict[str, Channel] = {}

    def logger(self, name: str | None = None) -> Logger:
        return Logger(self.channel(name))

    def channel(self, name: str | None = None) -> Channel:
        return self.configure_channel(name)

    def configure_channel(self, name: str | None = None) -> Channel:
        name = name or self.get_default_channel()

        if name in self._channels:
            return self._channels[name]

        config = self._configuration(name)

        self._channels[name] = self._create_channel(config)

        return self._channels[name]

    def _create_channel(self, raw_config: dict[str, Any]) -> Channel:
        config = ChannelConfig.model_validate(raw_config).root

        match config:
            case StreamConfig():
                return self._create_stream_channel(config)

            case ConsoleConfig():
                return self._create_console_channel(config)

    def _create_stream_channel(self, config: StreamConfig) -> Channel:
        logger = self._create_base_logger(config)

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

        logger.addHandler(handler)

        return Channel(logger)

    def _create_console_channel(self, config: ConsoleConfig) -> Channel:
        logger = self._create_base_logger(config)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)

        return Channel(logger)

    def get_default_channel(self) -> Channel:
        return self._app.config["logging.default"]

    def _create_base_logger(self, config: BaseConfig) -> logging.Logger:
        logger = logging.getLogger(self._app.config["app.name"].lower())
        logger.setLevel(config.level)

        return logger

    def _configuration(self, name: str) -> Any:
        loggers = self._app.config.get("logging.channels", {})

        if name not in loggers:
            raise ValueError(f"The logging channel [{name}] is not configured.")

        return loggers[name]
