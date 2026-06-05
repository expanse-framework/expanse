from __future__ import annotations

import json
import logging
import sys

from expanse.logging.formatters.structured import StructuredFormatter


def _make_record(
    msg: str = "test message",
    level: int = logging.INFO,
    exc_info: tuple | None = None,
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=None,
        exc_info=exc_info,
    )
    for k, v in extra.items():
        setattr(record, k, v)

    return record


def test_outputs_valid_json() -> None:
    formatter = StructuredFormatter()
    record = _make_record(msg="hello world")

    output = formatter.format(record)

    data = json.loads(output)
    assert isinstance(data, dict)


def test_includes_message() -> None:
    formatter = StructuredFormatter()
    record = _make_record(msg="structured message")

    output = formatter.format(record)

    data = json.loads(output)
    assert data["message"] == "structured message"


def test_includes_extra_attributes() -> None:
    formatter = StructuredFormatter()
    record = _make_record(request_id="abc-123", user_id=42)

    output = formatter.format(record)

    data = json.loads(output)
    assert data["request_id"] == "abc-123"
    assert data["user_id"] == 42


def test_includes_levelname_when_in_format() -> None:
    formatter = StructuredFormatter(fmt="%(levelname)s %(message)s")
    record = _make_record(level=logging.WARNING)

    output = formatter.format(record)

    data = json.loads(output)
    assert data["levelname"] == "WARNING"


def test_includes_asctime_when_in_format() -> None:
    formatter = StructuredFormatter(fmt="%(asctime)s %(message)s")
    record = _make_record()

    output = formatter.format(record)

    data = json.loads(output)
    assert "asctime" in data


def test_serializes_exception() -> None:
    formatter = StructuredFormatter()

    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()

    record = _make_record(exc_info=exc_info)

    output = formatter.format(record)

    data = json.loads(output)
    assert "exc_info" in data
    assert "ValueError" in data["exc_info"]
    assert "boom" in data["exc_info"]


def test_each_record_is_one_line() -> None:
    formatter = StructuredFormatter()
    record = _make_record(msg="line check")

    output = formatter.format(record)

    assert "\n" not in output
