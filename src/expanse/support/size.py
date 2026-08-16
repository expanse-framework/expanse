import re

from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core import core_schema


_SIZE_STRING_REGEX = re.compile(
    r"^(-?(?:\d+)?\.?\d+) *(b(?:ytes?)?)?(k(?:b|ilobytes?)?)?(m(?:b|egabytes?)?)?(g(?:b|igabytes?)?)?(t(?:b|erabytes?)?)?(p(?:b|etabytes?)?)?$"
)

_UNIT_FACTORS: dict[str, int] = {
    "bytes": 1,
    "kilobytes": 1024,
    "megabytes": 1024**2,
    "gigabytes": 1024**3,
    "terabytes": 1024**4,
    "petabytes": 1024**5,
}


@dataclass(slots=True, frozen=True)
class Size:
    value: float
    unit: Literal[
        "bytes", "kilobytes", "megabytes", "gigabytes", "terabytes", "petabytes"
    ]

    @classmethod
    def parse(cls, size: str | Self) -> Self:
        if isinstance(size, Size):
            return size

        match = _SIZE_STRING_REGEX.match(size)

        if not match:
            raise ValueError(f"Invalid size string: {size}")

        value = float(match.group(1))
        unit: Literal[
            "bytes", "kilobytes", "megabytes", "gigabytes", "terabytes", "petabytes"
        ] = "bytes"

        if match.group(3):
            unit = "kilobytes"
        elif match.group(4):
            unit = "megabytes"
        elif match.group(5):
            unit = "gigabytes"
        elif match.group(6):
            unit = "terabytes"
        elif match.group(7):
            unit = "petabytes"

        return cls(value, unit)

    def to_bytes(self) -> int:
        return int(self.value * _UNIT_FACTORS[self.unit])

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(Size.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(Size),
                    from_str_schema,
                ]
            ),
        )
