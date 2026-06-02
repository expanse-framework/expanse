from __future__ import annotations

import logging

import pytest

from expanse.logging.context import Context
from expanse.logging.filters.context import ContextFilter
from expanse.logging.utils import _set_context


def _make_record(msg: str = "test") -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )


def test_context_setitem_getitem() -> None:
    ctx = Context()
    ctx["key"] = "value"

    assert ctx["key"] == "value"


def test_context_getitem_raises_for_missing_key() -> None:
    ctx = Context()

    with pytest.raises(KeyError):
        _ = ctx["missing"]


def test_context_delitem() -> None:
    ctx = Context()
    ctx["key"] = "value"

    del ctx["key"]

    assert "key" not in ctx


def test_context_contains() -> None:
    ctx = Context()
    ctx["key"] = "value"

    assert "key" in ctx
    assert "other" not in ctx


def test_context_iter() -> None:
    ctx = Context()
    ctx["a"] = 1
    ctx["b"] = 2

    assert set(ctx) == {"a", "b"}


def test_context_len() -> None:
    ctx = Context()

    assert len(ctx) == 0

    ctx["x"] = 1
    assert len(ctx) == 1

    ctx["y"] = 2
    assert len(ctx) == 2


def test_context_get_with_default() -> None:
    ctx = Context()

    assert ctx.get("missing") is None
    assert ctx.get("missing", "default") == "default"

    ctx["key"] = "val"
    assert ctx.get("key") == "val"


def test_context_pop_existing_key() -> None:
    ctx = Context()
    ctx["key"] = "val"

    result = ctx.pop("key")

    assert result == "val"
    assert "key" not in ctx


def test_context_pop_missing_key_with_default() -> None:
    ctx = Context()

    assert ctx.pop("missing", None) is None


def test_context_popitem() -> None:
    ctx = Context()
    ctx["key"] = "val"

    item = ctx.popitem()

    assert item == ("key", "val")
    assert len(ctx) == 0


def test_context_clear() -> None:
    ctx = Context()
    ctx["a"] = 1
    ctx["b"] = 2

    ctx.clear()

    assert len(ctx) == 0


def test_context_update_from_dict() -> None:
    ctx = Context()

    ctx.update({"a": 1, "b": 2})

    assert ctx["a"] == 1
    assert ctx["b"] == 2


def test_context_update_from_kwargs() -> None:
    ctx = Context()

    ctx.update(x=10, y=20)

    assert ctx["x"] == 10
    assert ctx["y"] == 20


def test_context_setdefault_missing_key() -> None:
    ctx = Context()

    result = ctx.setdefault("key", "default")

    assert result == "default"
    assert ctx["key"] == "default"


def test_context_setdefault_existing_key_not_overwritten() -> None:
    ctx = Context()
    ctx["key"] = "original"

    result = ctx.setdefault("key", "other")

    assert result == "original"
    assert ctx["key"] == "original"


# ContextFilter tests


def test_context_filter_adds_context_to_record_when_set() -> None:
    ctx = Context()
    ctx["request_id"] = "xyz-789"
    _set_context(ctx)

    try:
        f = ContextFilter()
        record = _make_record()
        f.filter(record)

        assert record.context == {"request_id": "xyz-789"}  # type: ignore[attr-defined]
    finally:
        _set_context(None)


def test_context_filter_does_nothing_when_no_context() -> None:
    _set_context(None)

    f = ContextFilter()
    record = _make_record()
    f.filter(record)

    assert not hasattr(record, "context")


def test_context_filter_does_not_overwrite_existing_context_attribute() -> None:
    ctx = Context()
    ctx["key"] = "from_context"
    _set_context(ctx)

    try:
        f = ContextFilter()
        record = _make_record()
        record.context = {"key": "already_set"}  # type: ignore[attr-defined]
        f.filter(record)

        assert record.context == {"key": "already_set"}  # type: ignore[attr-defined]
    finally:
        _set_context(None)


def test_context_filter_always_returns_true() -> None:
    _set_context(None)

    f = ContextFilter()
    record = _make_record()

    assert f.filter(record) is True


def test_context_filter_reflects_context_mutations() -> None:
    ctx = Context()
    ctx["key"] = "initial"
    _set_context(ctx)

    try:
        ctx["key"] = "updated"

        f = ContextFilter()
        record = _make_record()
        f.filter(record)

        assert record.context["key"] == "updated"  # type: ignore[attr-defined]
    finally:
        _set_context(None)
