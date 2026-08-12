from typing import Literal

import pytest

from pydantic import BaseModel

from expanse.support.duration import SingleUnitDuration


class DurationModel(BaseModel):
    duration: SingleUnitDuration


@pytest.mark.parametrize(
    ("value", "expected_value", "expected_unit"),
    [
        ("5", 5, "milliseconds"),
        ("5ms", 5, "milliseconds"),
        ("5msec", 5, "milliseconds"),
        ("5msecs", 5, "milliseconds"),
        ("5millisecond", 5, "milliseconds"),
        ("5milliseconds", 5, "milliseconds"),
        ("5s", 5, "seconds"),
        ("5sec", 5, "seconds"),
        ("5secs", 5, "seconds"),
        ("5second", 5, "seconds"),
        ("5seconds", 5, "seconds"),
        ("5m", 5, "minutes"),
        ("5min", 5, "minutes"),
        ("5mins", 5, "minutes"),
        ("5minute", 5, "minutes"),
        ("5minutes", 5, "minutes"),
        ("5h", 5, "hours"),
        ("5hr", 5, "hours"),
        ("5hrs", 5, "hours"),
        ("5hour", 5, "hours"),
        ("5hours", 5, "hours"),
        ("5d", 5, "days"),
        ("5day", 5, "days"),
        ("5days", 5, "days"),
        ("5w", 5, "weeks"),
        ("5wk", 5, "weeks"),
        ("5wks", 5, "weeks"),
        ("5week", 5, "weeks"),
        ("5weeks", 5, "weeks"),
    ],
)
def test_parse_recognizes_unit_suffixes(
    value: str, expected_value: int, expected_unit: str
) -> None:
    duration = SingleUnitDuration.parse(value)

    assert duration.value == expected_value
    assert duration.unit == expected_unit


def test_parse_defaults_to_milliseconds_when_unit_is_missing() -> None:
    duration = SingleUnitDuration.parse("42")

    assert duration.value == 42
    assert duration.unit == "milliseconds"


def test_parse_allows_whitespace_between_value_and_unit() -> None:
    duration = SingleUnitDuration.parse("5 min")

    assert duration.value == 5
    assert duration.unit == "minutes"


def test_parse_accepts_negative_values() -> None:
    duration = SingleUnitDuration.parse("-3h")

    assert duration.value == -3
    assert duration.unit == "hours"


def test_parse_returns_same_instance_when_given_a_duration() -> None:
    original = SingleUnitDuration(1, "hours")

    assert SingleUnitDuration.parse(original) is original


@pytest.mark.parametrize("value", ["abc", "", "5x", "ms5"])
def test_parse_raises_on_invalid_string(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid single unit duration string"):
        SingleUnitDuration.parse(value)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (2, "weeks", 2 * 7 * 24 * 60 * 60),
        (3, "days", 3 * 24 * 60 * 60),
        (4, "hours", 4 * 60 * 60),
        (5, "minutes", 5 * 60),
        (6, "seconds", 6),
        (2000, "milliseconds", 2),
        (500, "milliseconds", 0),
    ],
)
def test_to_seconds_converts_units_correctly(
    value: int, unit: str, expected: int
) -> None:
    assert SingleUnitDuration(value, unit).to_seconds() == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (2, "weeks", 2 * 7 * 24 * 60 * 60 * 1000),
        (3, "days", 3 * 24 * 60 * 60 * 1000),
        (4, "hours", 4 * 60 * 60 * 1000),
        (5, "minutes", 5 * 60 * 1000),
        (6, "seconds", 6 * 1000),
        (7, "milliseconds", 7),
    ],
)
def test_to_milliseconds_converts_units_correctly(
    value: int,
    unit: Literal["weeks", "days", "hours", "minutes", "seconds", "milliseconds"],
    expected: int,
) -> None:
    assert SingleUnitDuration(value, unit).to_milliseconds() == expected


def test_pydantic_model_validates_from_string() -> None:
    model = DurationModel.model_validate({"duration": "10min"})

    assert model.duration == SingleUnitDuration(10, "minutes")


def test_pydantic_model_accepts_existing_duration_instance() -> None:
    duration = SingleUnitDuration(2, "hours")

    model = DurationModel(duration=duration)

    assert model.duration is duration


def test_pydantic_model_raises_on_invalid_duration_string() -> None:
    with pytest.raises(ValueError):
        DurationModel.model_validate({"duration": "not-a-duration"})
