from collections.abc import Callable
from logging import LogRecord
from logging.handlers import SysLogHandler
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import ImportString
from pydantic import field_validator

from expanse.support.duration import SingleUnitDuration


SyslogFacility = Literal[
    "auth",
    "authpriv",
    "console",
    "cron",
    "daemon",
    "ftp",
    "kern",
    "lpr",
    "mail",
    "news",
    "ntp",
    "security",
    "solaris-cron",
    "syslog",
    "user",
    "uucp",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "local6",
    "local7",
]


class BaseConfig(BaseModel):
    enabled: bool = True
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: str | None = None
    structured: bool = False
    processors: list[ImportString | Callable[[LogRecord], LogRecord]] = Field(
        default_factory=list
    )


class StreamConfig(BaseConfig):
    driver: Literal["stream"] = "stream"

    stream: str = "stderr"


class ConsoleConfig(BaseConfig):
    driver: Literal["console"] = "console"

    multiline: bool = False
    milliseconds: bool = False


class FileConfig(BaseConfig):
    driver: Literal["file"] = "file"

    path: Path


class TimeBasedConfig(BaseConfig):
    driver: Literal["time_based"] = "time_based"

    path: Path
    every: SingleUnitDuration | None = None
    on: (
        Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
        | None
    ) = None
    at: str | None = None
    max_files: int


class DailyConfig(BaseConfig):
    driver: Literal["daily"] = "daily"

    path: Path
    max_files: int = 30


class SyslogConfig(BaseConfig):
    driver: Literal["syslog"] = "syslog"

    address: str = "localhost:514"
    facility: SyslogFacility = "user"
    socket_type: Literal["udp", "tcp"] | None = None

    @field_validator("facility")
    @classmethod
    def validate_facility(cls, v: str) -> str:
        if v not in SysLogHandler.facility_names:
            raise ValueError(f"Invalid syslog facility: {v}")

        return v


class GroupConfig(BaseConfig):
    driver: Literal["group"] = "group"

    channels: list[str] = []

    @field_validator("channels", mode="before")
    @classmethod
    def decode_channels(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v

        return [v.strip() for v in v.split(",")]
