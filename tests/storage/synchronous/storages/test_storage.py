from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from obstore.store import LocalStore

from expanse.storage.synchronous.storages.storage import Storage


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> Storage:
    return Storage(LocalStore(tmp_path))


def test_put_and_get(store: Storage, tmp_path: Path) -> None:
    store.put("file.txt", b"hello world")

    result = store.get("file.txt")

    assert result == b"hello world"


def test_get_raises_for_missing_file(store: Storage) -> None:
    with pytest.raises(FileNotFoundError):
        store.get("missing.txt")


def test_put_overwrites_existing_file(store: Storage) -> None:
    store.put("file.txt", b"original")
    store.put("file.txt", b"updated")

    assert store.get("file.txt") == b"updated"


def test_exists_returns_true_for_existing_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "present.txt").write_bytes(b"data")

    assert store.exists("present.txt") is True


def test_exists_returns_false_for_missing_file(store: Storage) -> None:
    assert store.exists("absent.txt") is False


def test_delete_removes_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "to_delete.txt").write_bytes(b"bye")

    store.delete("to_delete.txt")

    assert not (tmp_path / "to_delete.txt").exists()


def test_delete_raises_for_missing_file(store: Storage) -> None:
    with pytest.raises(FileNotFoundError):
        store.delete("nonexistent.txt")


def test_copy_duplicates_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "source.txt").write_bytes(b"content")

    store.copy("source.txt", "copy.txt")

    assert (tmp_path / "source.txt").read_bytes() == b"content"
    assert (tmp_path / "copy.txt").read_bytes() == b"content"


def test_move_renames_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "before.txt").write_bytes(b"data")

    store.move("before.txt", "after.txt")

    assert not (tmp_path / "before.txt").exists()
    assert (tmp_path / "after.txt").read_bytes() == b"data"


def test_list_returns_all_files(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "b.txt").write_bytes(b"b")
    (tmp_path / "c.txt").write_bytes(b"c")

    files = store.list()

    assert sorted(files) == ["a.txt", "b.txt", "c.txt"]


def test_list_with_prefix_filters_results(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "logo.png").write_bytes(b"png")
    (tmp_path / "images" / "banner.png").write_bytes(b"png2")
    (tmp_path / "docs_readme.txt").write_bytes(b"txt")

    files = store.list("images")

    assert sorted(files) == ["images/banner.png", "images/logo.png"]


def test_list_returns_empty_for_empty_storage(store: Storage) -> None:
    files = store.list()

    assert files == []


def test_size_returns_byte_count(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "sized.txt").write_bytes(b"12345")

    assert store.size("sized.txt") == 5


def test_last_modified_returns_a_datetime(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "ts.txt").write_bytes(b"x")

    result = store.last_modified("ts.txt")

    assert isinstance(result, datetime)


def test_stream_yields_file_content(store: Storage, tmp_path: Path) -> None:
    content = b"streaming content"
    (tmp_path / "stream.txt").write_bytes(content)

    chunks = b""
    for chunk in store.stream("stream.txt"):
        chunks += bytes(chunk)

    assert chunks == content


def test_stream_with_small_chunk_size(store: Storage, tmp_path: Path) -> None:
    content = b"a" * 100
    (tmp_path / "chunked.txt").write_bytes(content)

    chunks = b""
    for chunk in store.stream("chunked.txt", chunk_size=10):
        chunks += bytes(chunk)

    assert chunks == content
