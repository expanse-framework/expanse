from __future__ import annotations

import pytest

from expanse.cache.synchronous.stores.memory import MemoryStore


@pytest.fixture()
def store() -> MemoryStore:
    return MemoryStore()


def test_set_stores_value(store: MemoryStore) -> None:
    result = store.set("key", "value")

    assert result is True
    assert store.get("key") == "value"


def test_set_overwrites_existing_key(store: MemoryStore) -> None:
    store.set("key", "original")
    store.set("key", "updated")

    assert store.get("key") == "updated"


def test_set_accepts_ttl_parameter(store: MemoryStore) -> None:
    result = store.set("key", "value", ttl=60)

    assert result is True
    assert store.get("key") == "value"


def test_set_many_stores_multiple_values(store: MemoryStore) -> None:
    result = store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert store.get("a") == 1
    assert store.get("b") == 2
    assert store.get("c") == 3


def test_set_many_overwrites_existing_keys(store: MemoryStore) -> None:
    store.set("key", "original")
    store.set_many({"key": "updated", "new": "value"})

    assert store.get("key") == "updated"
    assert store.get("new") == "value"


def test_get_returns_stored_value(store: MemoryStore) -> None:
    store.set("key", "value")

    assert store.get("key") == "value"


def test_get_returns_none_for_missing_key(store: MemoryStore) -> None:
    assert store.get("missing") is None


def test_get_many_returns_values_for_existing_keys(store: MemoryStore) -> None:
    store.set_many({"x": 10, "y": 20})

    result = store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


def test_get_many_returns_none_for_missing_keys(store: MemoryStore) -> None:
    store.set("x", 10)

    result = store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


def test_has_returns_true_for_existing_key(store: MemoryStore) -> None:
    store.set("key", "value")

    assert store.has("key") is True


def test_has_returns_false_for_missing_key(store: MemoryStore) -> None:
    assert store.has("missing") is False


def test_delete_removes_key(store: MemoryStore) -> None:
    store.set("key", "value")

    result = store.delete("key")

    assert result is True
    assert store.get("key") is None


def test_delete_returns_false_for_missing_key(store: MemoryStore) -> None:
    result = store.delete("missing")

    assert result is False


def test_clear_removes_all_keys(store: MemoryStore) -> None:
    store.set_many({"a": 1, "b": 2})

    result = store.clear()

    assert result is True
    assert store.get("a") is None
    assert store.get("b") is None


def test_stores_various_value_types(store: MemoryStore) -> None:
    store.set("int", 42)
    store.set("list", [1, 2, 3])
    store.set("dict", {"nested": True})

    assert store.get("int") == 42
    assert store.get("list") == [1, 2, 3]
    assert store.get("dict") == {"nested": True}
