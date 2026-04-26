from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from obstore.store import LocalStore

from expanse.storage.asynchronous.storages.storage import Storage


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def store(tmp_path: Path) -> Storage:
    return Storage(LocalStore(tmp_path))


async def test_put_and_get(store: Storage, tmp_path: Path) -> None:
    await store.put("file.txt", b"hello world")

    result = await store.get("file.txt")

    assert result == b"hello world"


async def test_get_raises_for_missing_file(store: Storage) -> None:
    with pytest.raises(FileNotFoundError):
        await store.get("missing.txt")


async def test_put_overwrites_existing_file(store: Storage) -> None:
    await store.put("file.txt", b"original")
    await store.put("file.txt", b"updated")

    assert await store.get("file.txt") == b"updated"


async def test_exists_returns_true_for_existing_file(
    store: Storage, tmp_path: Path
) -> None:
    (tmp_path / "present.txt").write_bytes(b"data")

    assert await store.exists("present.txt") is True


async def test_exists_returns_false_for_missing_file(store: Storage) -> None:
    assert await store.exists("absent.txt") is False


async def test_delete_removes_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "to_delete.txt").write_bytes(b"bye")

    await store.delete("to_delete.txt")

    assert not (tmp_path / "to_delete.txt").exists()


async def test_delete_raises_for_missing_file(store: Storage) -> None:
    with pytest.raises(FileNotFoundError):
        await store.delete("nonexistent.txt")


async def test_copy_duplicates_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "source.txt").write_bytes(b"content")

    await store.copy("source.txt", "copy.txt")

    assert (tmp_path / "source.txt").read_bytes() == b"content"
    assert (tmp_path / "copy.txt").read_bytes() == b"content"


async def test_move_renames_a_file(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "before.txt").write_bytes(b"data")

    await store.move("before.txt", "after.txt")

    assert not (tmp_path / "before.txt").exists()
    assert (tmp_path / "after.txt").read_bytes() == b"data"


async def test_list_returns_all_files(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "b.txt").write_bytes(b"b")
    (tmp_path / "c.txt").write_bytes(b"c")

    files = await store.list()

    assert sorted(files) == ["a.txt", "b.txt", "c.txt"]


async def test_list_with_prefix_filters_results(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "logo.png").write_bytes(b"png")
    (tmp_path / "images" / "banner.png").write_bytes(b"png2")
    (tmp_path / "docs_readme.txt").write_bytes(b"txt")

    files = await store.list("images")

    assert sorted(files) == ["images/banner.png", "images/logo.png"]


async def test_list_returns_empty_for_empty_storage(store: Storage) -> None:
    files = await store.list()

    assert files == []


async def test_size_returns_byte_count(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "sized.txt").write_bytes(b"12345")

    assert await store.size("sized.txt") == 5


async def test_last_modified_returns_a_datetime(store: Storage, tmp_path: Path) -> None:
    (tmp_path / "ts.txt").write_bytes(b"x")

    result = await store.last_modified("ts.txt")

    assert isinstance(result, datetime)


async def test_stream_yields_file_content(store: Storage, tmp_path: Path) -> None:
    content = b"streaming content"
    (tmp_path / "stream.txt").write_bytes(content)

    iterator = await store.stream("stream.txt")

    chunks = b""
    async for chunk in iterator:
        chunks += bytes(chunk)

    assert chunks == content


async def test_stream_with_small_chunk_size(store: Storage, tmp_path: Path) -> None:
    content = b"a" * 100
    (tmp_path / "chunked.txt").write_bytes(content)

    iterator = await store.stream("chunked.txt", chunk_size=10)

    chunks = b""
    async for chunk in iterator:
        chunks += bytes(chunk)

    assert chunks == content


async def test_as_download_returns_a_file_response(
    store: Storage, tmp_path: Path
) -> None:
    from expanse.http.responses.file import FileResponse

    (tmp_path / "report.csv").write_bytes(b"a,b,c\n1,2,3\n")

    response = await store.as_download("report.csv")

    assert isinstance(response, FileResponse)


async def test_as_download_sets_filename_and_content_disposition(
    store: Storage, tmp_path: Path
) -> None:
    from expanse.http.responses.file import FileResponse

    (tmp_path / "report.csv").write_bytes(b"a,b,c\n")

    response = await store.as_download("report.csv")

    assert isinstance(response, FileResponse)
    assert response.filename == "report.csv"
    assert response.content_disposition == "attachment"


async def test_as_download_metadata_includes_file_size(
    store: Storage, tmp_path: Path
) -> None:
    content = b"hello from storage"
    (tmp_path / "data.txt").write_bytes(content)

    response = await store.as_download("data.txt")

    assert response.metadata.get("size") == len(content)


async def test_as_download_iterator_yields_full_content(
    store: Storage, tmp_path: Path
) -> None:
    content = b"hello from storage"
    (tmp_path / "data.txt").write_bytes(content)

    response = await store.as_download("data.txt")

    collected = b""
    async for chunk in response.iterator():
        collected += bytes(chunk)

    assert collected == content


async def test_as_download_iterator_yields_multiple_chunks_for_large_file(
    store: Storage, tmp_path: Path
) -> None:
    # Write a file larger than the 64KB chunk size used in as_download()
    content = b"x" * (128 * 1024 + 1)
    (tmp_path / "large.bin").write_bytes(content)

    response = await store.as_download("large.bin")

    chunks: list[bytes] = []
    async for chunk in response.iterator():
        chunks.append(bytes(chunk))

    assert len(chunks) > 1, "large file should be streamed in multiple chunks"
    assert b"".join(chunks) == content
