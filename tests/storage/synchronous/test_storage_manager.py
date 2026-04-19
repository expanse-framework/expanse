from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.configuration.config import Config
from expanse.storage.exceptions import UnconfiguredStorageError
from expanse.storage.exceptions import UnsupportedStorageDriverError
from expanse.storage.synchronous.storage_manager import StorageManager
from expanse.storage.synchronous.storages.storage import Storage


if TYPE_CHECKING:
    from pathlib import Path

    from expanse.core.application import Application


@pytest.fixture()
def local_config(tmp_path: Path) -> Config:
    secondary = tmp_path / "secondary"
    secondary.mkdir()

    return Config(
        {
            "storage": {
                "storage": "local",
                "storages": {
                    "local": {"driver": "local", "root": str(tmp_path)},
                    "secondary": {
                        "driver": "local",
                        "root": str(secondary),
                    },
                },
            }
        }
    )


@pytest.fixture()
def manager(app: Application, local_config: Config) -> StorageManager:
    return StorageManager(app, local_config)


def test_storage_manager_returns_default_storage(manager: StorageManager) -> None:
    storage = manager.storage()

    assert isinstance(storage, Storage)


def test_storage_manager_returns_named_storage(manager: StorageManager) -> None:
    storage = manager.storage("secondary")

    assert isinstance(storage, Storage)


def test_storage_manager_caches_storage_instances(manager: StorageManager) -> None:
    first = manager.storage()
    second = manager.storage()

    assert first is second


def test_storage_manager_caches_named_storage_instances(
    manager: StorageManager,
) -> None:
    first = manager.storage("secondary")
    second = manager.storage("secondary")

    assert first is second


def test_storage_manager_raises_for_unknown_storage(
    manager: StorageManager, local_config: Config
) -> None:
    local_config["storage"]["storage"] = "unknown"
    with pytest.raises(
        UnconfiguredStorageError, match=r"The storage 'unknown' is not configured."
    ):
        manager.storage("unknown")


def test_storage_manager_raises_for_unsupported_driver(
    app: Application, tmp_path: Path
) -> None:
    config = Config(
        {
            "storage": {
                "storage": "bad",
                "storages": {"bad": {"driver": "invalid"}},
            }
        }
    )
    manager = StorageManager(app, config)

    with pytest.raises(
        UnsupportedStorageDriverError, match="Unsupported storage type: invalid"
    ):
        manager.storage()


def test_storage_manager_get_default_storage_name(manager: StorageManager) -> None:
    assert manager.get_default_storage_name() == "local"


def test_storage_manager_delegates_get(manager: StorageManager, tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_bytes(b"hello")

    result = manager.get("hello.txt")

    assert result == b"hello"


def test_storage_manager_delegates_put(manager: StorageManager, tmp_path: Path) -> None:
    manager.put("greeting.txt", b"world")

    assert (tmp_path / "greeting.txt").read_bytes() == b"world"


def test_storage_manager_delegates_exists(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "exists.txt").write_bytes(b"data")

    assert manager.exists("exists.txt") is True
    assert manager.exists("missing.txt") is False


def test_storage_manager_delegates_delete(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "to_delete.txt").write_bytes(b"bye")

    manager.delete("to_delete.txt")

    assert not (tmp_path / "to_delete.txt").exists()


def test_storage_manager_delegates_list(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "b.txt").write_bytes(b"b")

    files = manager.list()

    assert sorted(files) == ["a.txt", "b.txt"]


def test_storage_manager_delegates_size(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "sized.txt").write_bytes(b"12345")

    assert manager.size("sized.txt") == 5


def test_storage_manager_delegates_copy(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "source.txt").write_bytes(b"copied")

    manager.copy("source.txt", "dest.txt")

    assert (tmp_path / "source.txt").read_bytes() == b"copied"
    assert (tmp_path / "dest.txt").read_bytes() == b"copied"


def test_storage_manager_delegates_move(
    manager: StorageManager, tmp_path: Path
) -> None:
    (tmp_path / "original.txt").write_bytes(b"moved")

    manager.move("original.txt", "renamed.txt")

    assert not (tmp_path / "original.txt").exists()
    assert (tmp_path / "renamed.txt").read_bytes() == b"moved"
