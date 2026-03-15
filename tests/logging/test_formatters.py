from __future__ import annotations

import logging

from expanse.logging.formatters.console import ConsoleFormatter


def _make_record(
    msg: str = "test message",
    level: int = logging.INFO,
    args: tuple | dict | None = None,
    exc_info: tuple | None = None,
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=args,
        exc_info=exc_info,
    )
    for k, v in extra.items():
        setattr(record, k, v)

    return record


def test_format_includes_level() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(level=logging.INFO)

    output = formatter.format(record)

    assert "INFO" in output


def test_format_includes_message() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(msg="hello world")

    output = formatter.format(record)

    assert "hello world" in output


def test_format_includes_time() -> None:
    formatter = ConsoleFormatter()
    record = _make_record()

    output = formatter.format(record)

    # Time format is HH:mm:ss, so we check for colon-separated digits
    import re

    assert re.search(r"\d{2}:\d{2}:\d{2}", output)


def test_format_with_tuple_args() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(msg="hello %s", args=("world",))

    output = formatter.format(record)

    assert "world" in output


def test_format_with_dict_args() -> None:
    formatter = ConsoleFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="value is %(val)s",
        args=None,
        exc_info=None,
    )
    # Set args directly to bypass LogRecord.__init__ unpacking
    record.args = {"val": "42"}

    output = formatter.format(record)

    assert "42" in output


def test_format_includes_extra_attributes() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(request_id="abc-123")

    output = formatter.format(record)

    assert "request_id" in output
    assert "abc-123" in output


def test_format_with_exception() -> None:
    formatter = ConsoleFormatter()

    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = _make_record(exc_info=exc_info)

    output = formatter.format(record)

    assert "ValueError" in output
    assert "boom" in output


def test_format_debug_level() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(level=logging.DEBUG)

    output = formatter.format(record)

    assert "DEBU" in output


def test_format_warning_level() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(level=logging.WARNING)

    output = formatter.format(record)

    assert "WARN" in output


def test_format_error_level() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(level=logging.ERROR)

    output = formatter.format(record)

    assert "ERRO" in output


def test_format_critical_level() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(level=logging.CRITICAL)

    output = formatter.format(record)

    assert "CRIT" in output


def test_format_without_args() -> None:
    formatter = ConsoleFormatter()
    record = _make_record(msg="no args here")

    output = formatter.format(record)

    assert "no args here" in output
