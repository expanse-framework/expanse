import pytest

from pydantic import BaseModel

from expanse.support.size import Size


class SizeModel(BaseModel):
    size: Size


@pytest.mark.parametrize(
    ("value", "expected_value", "expected_unit"),
    [
        ("5", 5, "bytes"),
        ("5b", 5, "bytes"),
        ("5byte", 5, "bytes"),
        ("5bytes", 5, "bytes"),
        ("5k", 5, "kilobytes"),
        ("5kb", 5, "kilobytes"),
        ("5kilobyte", 5, "kilobytes"),
        ("5kilobytes", 5, "kilobytes"),
        ("5m", 5, "megabytes"),
        ("5mb", 5, "megabytes"),
        ("5megabyte", 5, "megabytes"),
        ("5megabytes", 5, "megabytes"),
        ("5g", 5, "gigabytes"),
        ("5gb", 5, "gigabytes"),
        ("5gigabyte", 5, "gigabytes"),
        ("5gigabytes", 5, "gigabytes"),
        ("5t", 5, "terabytes"),
        ("5tb", 5, "terabytes"),
        ("5terabyte", 5, "terabytes"),
        ("5terabytes", 5, "terabytes"),
        ("5p", 5, "petabytes"),
        ("5pb", 5, "petabytes"),
        ("5petabyte", 5, "petabytes"),
        ("5petabytes", 5, "petabytes"),
    ],
)
def test_parse_recognizes_unit_suffixes(
    value: str, expected_value: float, expected_unit: str
) -> None:
    size = Size.parse(value)

    assert size.value == expected_value
    assert size.unit == expected_unit


def test_parse_defaults_to_bytes_when_unit_is_missing() -> None:
    size = Size.parse("42")

    assert size.value == 42
    assert size.unit == "bytes"


def test_parse_allows_whitespace_between_value_and_unit() -> None:
    size = Size.parse("5 mb")

    assert size.value == 5
    assert size.unit == "megabytes"


def test_parse_accepts_negative_values() -> None:
    size = Size.parse("-3gb")

    assert size.value == -3
    assert size.unit == "gigabytes"


def test_parse_accepts_decimal_values() -> None:
    size = Size.parse("1.5gb")

    assert size.value == 1.5
    assert size.unit == "gigabytes"


def test_parse_returns_same_instance_when_given_a_size() -> None:
    original = Size(1, "gigabytes")

    assert Size.parse(original) is original


@pytest.mark.parametrize("value", ["abc", "", "5x", "mb5"])
def test_parse_raises_on_invalid_string(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid size string"):
        Size.parse(value)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (5, "bytes", 5),
        (2, "kilobytes", 2 * 1024),
        (3, "megabytes", 3 * 1024**2),
        (4, "gigabytes", 4 * 1024**3),
        (1, "terabytes", 1024**4),
        (1, "petabytes", 1024**5),
        (1.5, "gigabytes", int(1.5 * 1024**3)),
    ],
)
def test_to_bytes_converts_units_correctly(
    value: float, unit: str, expected: int
) -> None:
    assert Size(value, unit).to_bytes() == expected  # type: ignore[arg-type]


def test_pydantic_model_validates_from_string() -> None:
    model = SizeModel.model_validate({"size": "10mb"})

    assert model.size == Size(10, "megabytes")


def test_pydantic_model_accepts_existing_size_instance() -> None:
    size = Size(2, "gigabytes")

    model = SizeModel(size=size)

    assert model.size is size


def test_pydantic_model_raises_on_invalid_size_string() -> None:
    with pytest.raises(ValueError):
        SizeModel.model_validate({"size": "not-a-size"})
