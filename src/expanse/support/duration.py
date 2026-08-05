import re

from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core import core_schema


_DURATION_STRING_REGEX = re.compile(
    r"^(-?(?:\d+)?\.?\d+) *(m(?:illiseconds?|s(?:ecs?)?))?(s(?:ec(?:onds?|s)?)?)?(m(?:in(?:utes?|s)?)?)?(h(?:ours?|rs?)?)?(d(?:ays?)?)?(w(?:eeks?|ks?)?)?$"
)


@dataclass(slots=True, frozen=True)
class SingleUnitDuration:
    value: int
    unit: Literal["weeks", "days", "hours", "minutes", "seconds", "milliseconds"]

    @classmethod
    def parse(cls, duration: str | Self) -> Self:
        if isinstance(duration, SingleUnitDuration):
            return duration

        match = _DURATION_STRING_REGEX.match(duration)

        if not match:
            raise ValueError(f"Invalid single unit duration string: {duration}")

        value = int(match.group(1))
        unit: Literal[
            "weeks", "days", "hours", "minutes", "seconds", "milliseconds"
        ] = "milliseconds"

        if match.group(3):
            unit = "seconds"
        elif match.group(4):
            unit = "minutes"
        elif match.group(5):
            unit = "hours"
        elif match.group(6):
            unit = "days"
        elif match.group(7):
            unit = "weeks"

        return cls(value, unit)

    def to_seconds(self) -> int:
        match self.unit:
            case "weeks":
                return self.value * 7 * 24 * 60 * 60
            case "days":
                return self.value * 24 * 60 * 60
            case "hours":
                return self.value * 60 * 60
            case "minutes":
                return self.value * 60
            case "seconds":
                return self.value
            case "milliseconds":
                return self.value // 1000

    def to_milliseconds(self) -> int:
        match self.unit:
            case "weeks":
                return self.value * 7 * 24 * 60 * 60 * 1000
            case "days":
                return self.value * 24 * 60 * 60 * 1000
            case "hours":
                return self.value * 60 * 60 * 1000
            case "minutes":
                return self.value * 60 * 1000
            case "seconds":
                return self.value * 1000
            case "milliseconds":
                return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(SingleUnitDuration.parse),
            ]
        )
        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(SingleUnitDuration),
                    from_str_schema,
                ]
            ),
        )
