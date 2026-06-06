from __future__ import annotations

import time

from typing import TYPE_CHECKING

import pytest

from expanse.cache.asynchronous.stores.file.store import FileStore
from expanse.cache.synchronous.stores.file.store import FileStore as SyncFileStore


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> FileStore:
    return FileStore(SyncFileStore(tmp_path / "cache"))


async def test_set_stores_value(store: FileStore) -> None:
    result = await store.set("key", "value")

    assert result is True
    assert (await store.get("key")).value == "value"


async def test_set_overwrites_existing_key(store: FileStore) -> None:
    await store.set("key", "original")
    await store.set("key", "updated")

    assert (await store.get("key")).value == "updated"


async def test_set_with_ttl_stores_value(store: FileStore) -> None:
    result = await store.set("key", "value", ttl=60)

    assert result is True
    assert (await store.get("key")).value == "value"


async def test_set_with_expired_ttl_returns_miss(store: FileStore) -> None:
    await store.set("key", "value", ttl=1)

    path = store._sync_store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    assert (await store.get("key")).is_hit is False


async def test_set_many_stores_multiple_values(store: FileStore) -> None:
    result = await store.set_many({"a": 1, "b": 2, "c": 3})

    assert result is True
    assert (await store.get("a")).value == 1
    assert (await store.get("b")).value == 2
    assert (await store.get("c")).value == 3


async def test_set_many_overwrites_existing_keys(store: FileStore) -> None:
    await store.set("key", "original")
    await store.set_many({"key": "updated", "new": "value"})

    assert (await store.get("key")).value == "updated"
    assert (await store.get("new")).value == "value"


async def test_get_returns_stored_value(store: FileStore) -> None:
    await store.set("key", "value")

    item = await store.get("key")

    assert item.is_hit is True
    assert item.value == "value"


async def test_get_returns_miss_for_missing_key(store: FileStore) -> None:
    assert (await store.get("missing")).is_hit is False


async def test_get_deletes_expired_file(store: FileStore) -> None:
    await store.set("key", "value", ttl=1)

    path = store._sync_store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    await store.get("key")

    assert not path.exists()


async def test_get_many_returns_hits_for_existing_keys(store: FileStore) -> None:
    await store.set_many({"x": 10, "y": 20})

    result = await store.get_many(["x", "y"])

    assert result["x"].is_hit is True
    assert result["x"].value == 10
    assert result["y"].is_hit is True
    assert result["y"].value == 20


async def test_get_many_returns_miss_for_missing_keys(store: FileStore) -> None:
    await store.set("x", 10)

    result = await store.get_many(["x", "missing"])

    assert result["x"].is_hit is True
    assert result["x"].value == 10
    assert result["missing"].is_hit is False


async def test_get_many_returns_empty_dict_for_empty_keys(store: FileStore) -> None:
    result = await store.get_many([])

    assert result == {}


async def test_has_returns_true_for_existing_key(store: FileStore) -> None:
    await store.set("key", "value")

    assert await store.has("key") is True


async def test_has_returns_false_for_missing_key(store: FileStore) -> None:
    assert await store.has("missing") is False


async def test_has_returns_false_for_expired_key(store: FileStore) -> None:
    await store.set("key", "value", ttl=1)

    path = store._sync_store._path_for_key("key")
    content = path.read_text()
    _expiration, value_hex = content.split("\n", 1)
    path.write_text(f"{int(time.time()) - 1}\n{value_hex}")

    assert await store.has("key") is False


async def test_delete_removes_key(store: FileStore) -> None:
    await store.set("key", "value")

    result = await store.delete("key")

    assert result is True
    assert (await store.get("key")).is_hit is False


async def test_delete_returns_false_for_missing_key(store: FileStore) -> None:
    result = await store.delete("missing")

    assert result is False


async def test_clear_removes_all_keys(store: FileStore) -> None:
    await store.set_many({"a": 1, "b": 2})

    result = await store.clear()

    assert result is True
    assert (await store.get("a")).is_hit is False
    assert (await store.get("b")).is_hit is False


async def test_stores_various_value_types(store: FileStore) -> None:
    await store.set("int", 42)
    await store.set("list", [1, 2, 3])
    await store.set("dict", {"nested": True})

    assert (await store.get("int")).value == 42
    assert (await store.get("list")).value == [1, 2, 3]
    assert (await store.get("dict")).value == {"nested": True}
