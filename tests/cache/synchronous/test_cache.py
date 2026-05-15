from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from expanse.cache.synchronous.cache import Cache
from expanse.cache.synchronous.stores.memory import MemoryStore


@pytest.fixture()
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture()
def cache(store: MemoryStore) -> Cache:
    return Cache(store)


def test_set_stores_value(cache: Cache) -> None:
    result = cache.set("key", "value")

    assert result is True
    assert cache.get("key") == "value"


def test_set_with_ttl_stores_value(cache: Cache) -> None:
    result = cache.set("key", "value", ttl=60)

    assert result is True
    assert cache.get("key") == "value"


def test_set_with_until_stores_value(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    result = cache.set("key", "value", until=until)

    assert result is True
    assert cache.get("key") == "value"


def test_set_raises_when_both_ttl_and_until_given(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    with pytest.raises(
        ValueError, match=r"Cannot specify both 'ttl' and 'until' parameters."
    ):
        cache.set("key", "value", ttl=60, until=until)


def test_set_with_zero_ttl_deletes_existing_key(cache: Cache) -> None:
    cache.set("key", "value")

    result = cache.set("key", "new_value", ttl=0)

    assert result is True
    assert cache.get("key") is None


def test_set_with_negative_ttl_deletes_existing_key(cache: Cache) -> None:
    cache.set("key", "value")

    result = cache.set("key", "new_value", ttl=-10)

    assert result is True
    assert cache.get("key") is None


def test_set_with_expired_until_deletes_existing_key(cache: Cache) -> None:
    cache.set("key", "value")
    past = datetime.now(UTC) - timedelta(seconds=1)

    result = cache.set("key", "new_value", until=past)

    assert result is True
    assert cache.get("key") is None


def test_set_many_stores_multiple_values(cache: Cache) -> None:
    result = cache.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_set_many_with_ttl_stores_values(cache: Cache) -> None:
    result = cache.set_many({"a": 1, "b": 2}, ttl=60)

    assert result is True
    assert cache.get("a") == 1
    assert cache.get("b") == 2


def test_set_many_with_until_stores_values(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    result = cache.set_many({"a": 1, "b": 2}, until=until)

    assert result is True
    assert cache.get("a") == 1
    assert cache.get("b") == 2


def test_set_many_raises_when_both_ttl_and_until_given(cache: Cache) -> None:
    until = datetime.now(UTC) + timedelta(seconds=60)

    with pytest.raises(
        ValueError, match=r"Cannot specify both 'ttl' and 'until' parameters."
    ):
        cache.set_many({"a": 1}, ttl=60, until=until)


def test_set_many_with_zero_ttl_deletes_existing_keys(cache: Cache) -> None:
    cache.set_many({"a": 1, "b": 2})

    result = cache.set_many({"a": 99, "b": 99}, ttl=0)

    assert result is True
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_get_returns_stored_value(cache: Cache) -> None:
    cache.set("key", "value")

    assert cache.get("key") == "value"


def test_get_returns_none_for_missing_key(cache: Cache) -> None:
    assert cache.get("missing") is None


def test_get_returns_default_for_missing_key(cache: Cache) -> None:
    assert cache.get("missing", "fallback") == "fallback"


def test_get_returns_stored_value_ignoring_default(cache: Cache) -> None:
    cache.set("key", "value")

    assert cache.get("key", "fallback") == "value"


def test_get_many_with_list_returns_all_values(cache: Cache) -> None:
    cache.set_many({"x": 10, "y": 20})

    result = cache.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


def test_get_many_with_list_returns_none_for_missing(cache: Cache) -> None:
    cache.set("x", 10)

    result = cache.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


def test_get_many_with_dict_uses_dict_keys(cache: Cache) -> None:
    cache.set_many({"x": 10, "y": 20})

    result = cache.get_many({"x": None, "y": None})

    assert result == {"x": 10, "y": 20}


def test_has_returns_true_for_existing_key(cache: Cache) -> None:
    cache.set("key", "value")

    assert cache.has("key") is True


def test_has_returns_false_for_missing_key(cache: Cache) -> None:
    assert cache.has("missing") is False


def test_has_returns_false_after_deletion(cache: Cache) -> None:
    cache.set("key", "value")
    cache.delete("key")

    assert cache.has("key") is False


def test_pop_returns_value_and_removes_key(cache: Cache) -> None:
    cache.set("key", "value")

    result = cache.pop("key")

    assert result == "value"
    assert cache.has("key") is False


def test_pop_returns_none_for_missing_key(cache: Cache) -> None:
    result = cache.pop("missing")

    assert result is None


def test_delete_removes_key(cache: Cache) -> None:
    cache.set("key", "value")

    result = cache.delete("key")

    assert result is True
    assert cache.get("key") is None


def test_delete_returns_false_for_missing_key(cache: Cache) -> None:
    result = cache.delete("missing")

    assert result is False


def test_delete_many_removes_all_keys(cache: Cache) -> None:
    cache.set_many({"a": 1, "b": 2, "c": 3})

    result = cache.delete_many(["a", "b", "c"])

    assert result is True
    assert cache.get("a") is None
    assert cache.get("b") is None
    assert cache.get("c") is None


def test_delete_many_returns_false_when_key_missing(cache: Cache) -> None:
    cache.set("a", 1)

    result = cache.delete_many(["a", "missing"])

    assert result is False
    assert cache.get("a") is None


def test_clear_removes_all_keys(cache: Cache) -> None:
    cache.set_many({"a": 1, "b": 2})

    result = cache.clear()

    assert result is True
    assert cache.get("a") is None
    assert cache.get("b") is None
