from __future__ import annotations

import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.synchronous.stores.file.store import FileStore


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> FileStore:
    return FileStore(tmp_path / "cache")


def test_set_stores_value(store: FileStore) -> None:
    result = store.set("key", "value")

    assert result is True
    assert store.get("key") == "value"


def test_set_overwrites_existing_key(store: FileStore) -> None:
    store.set("key", "original")
    store.set("key", "updated")

    assert store.get("key") == "updated"


def test_set_with_ttl_stores_value(store: FileStore) -> None:
    result = store.set("key", "value", ttl=60)

    assert result is True
    assert store.get("key") == "value"


def test_set_with_expired_ttl_returns_none(store: FileStore) -> None:
    store.set("key", "value", ttl=1)

    path = store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    assert store.get("key") is None


def test_set_many_stores_multiple_values(store: FileStore) -> None:
    result = store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert store.get("a") == 1
    assert store.get("b") == 2
    assert store.get("c") == 3


def test_set_many_overwrites_existing_keys(store: FileStore) -> None:
    store.set("key", "original")
    store.set_many({"key": "updated", "new": "value"})

    assert store.get("key") == "updated"
    assert store.get("new") == "value"


def test_get_returns_stored_value(store: FileStore) -> None:
    store.set("key", "value")

    assert store.get("key") == "value"


def test_get_returns_none_for_missing_key(store: FileStore) -> None:
    assert store.get("missing") is None


def test_get_deletes_expired_file(store: FileStore) -> None:
    store.set("key", "value", ttl=1)

    path = store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    store.get("key")

    assert not path.exists()


def test_get_many_returns_values_for_existing_keys(store: FileStore) -> None:
    store.set_many({"x": 10, "y": 20})

    result = store.get_many(["x", "y"])

    assert result == {"x": 10, "y": 20}


def test_get_many_returns_none_for_missing_keys(store: FileStore) -> None:
    store.set("x", 10)

    result = store.get_many(["x", "missing"])

    assert result == {"x": 10, "missing": None}


def test_get_many_returns_empty_dict_for_empty_keys(store: FileStore) -> None:
    result = store.get_many([])

    assert result == {}


def test_has_returns_true_for_existing_key(store: FileStore) -> None:
    store.set("key", "value")

    assert store.has("key") is True


def test_has_returns_false_for_missing_key(store: FileStore) -> None:
    assert store.has("missing") is False


def test_has_returns_false_for_expired_key(store: FileStore) -> None:
    store.set("key", "value", ttl=1)

    path = store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    assert store.has("key") is False


def test_delete_removes_key(store: FileStore) -> None:
    store.set("key", "value")

    result = store.delete("key")

    assert result is True
    assert store.get("key") is None


def test_delete_returns_false_for_missing_key(store: FileStore) -> None:
    result = store.delete("missing")

    assert result is False


def test_clear_removes_all_keys(store: FileStore) -> None:
    store.set_many({"a": 1, "b": 2})

    result = store.clear()

    assert result is True
    assert store.get("a") is None
    assert store.get("b") is None


def test_stores_various_value_types(store: FileStore) -> None:
    store.set("int", 42)
    store.set("list", [1, 2, 3])
    store.set("dict", {"nested": True})

    assert store.get("int") == 42
    assert store.get("list") == [1, 2, 3]
    assert store.get("dict") == {"nested": True}


def test_creates_cache_directory_if_not_exists(tmp_path: Path) -> None:
    cache_dir = tmp_path / "new" / "nested" / "cache"

    assert not cache_dir.exists()

    FileStore(cache_dir)

    assert cache_dir.exists()


def test_no_expiration_value_is_never_expired(store: FileStore) -> None:
    store.set("key", "value")

    path = store._path_for_key("key")
    expiration_str = path.read_text().split("\n", 1)[0]

    assert expiration_str == "0"
    assert store.get("key") == "value"
