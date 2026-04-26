from collections.abc import Buffer
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING
from typing import cast

from expanse.http.responses.file import FileResponse
from expanse.http.responses.streamed import StreamedResponse


if TYPE_CHECKING:
    from obstore.store import _ObjectStoreMixin

from expanse.contracts.storage.synchronous.storage import Storage as StorageContract


class Storage(StorageContract):
    def __init__(self, store: "_ObjectStoreMixin") -> None:
        self._store: _ObjectStoreMixin = store

    def get(self, path: str) -> bytes:
        result = self._store.get(path)

        return result.buffer().to_bytes()

    def stream(self, path: str, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        result = self._store.get(path)

        return result.stream(chunk_size)

    def put(
        self,
        path: str,
        content: (
            IO[bytes] | Path | bytes | Buffer | Iterator[Buffer] | Iterable[Buffer]
        ),
    ) -> None:
        self._store.put(path, content)

    def delete(self, path: str) -> None:
        self._store.delete(path)

    def copy(self, source: str, destination: str) -> None:
        self._store.copy(source, destination)

    def move(self, source: str, destination: str) -> None:
        self._store.rename(source, destination)

    def exists(self, path: str) -> bool:
        try:
            self._store.head(path)
            return True
        except FileNotFoundError:
            return False

    def list(self, prefix: str = "") -> list[str]:
        return [meta["path"] for chunk in self._store.list(prefix) for meta in chunk]

    def size(self, path: str) -> int:
        metadata = self._store.head(path)

        return metadata["size"]

    def last_modified(self, path: str) -> datetime:
        metadata = self._store.head(path)

        return metadata["last_modified"]

    def metadata(self, path: str) -> dict[str, int | datetime | str]:
        metadata = self._store.head(path)

        return {
            "size": metadata["size"],
            "last_modified": metadata["last_modified"],
            "etag": metadata["e_tag"] or "",
        }

    def as_download(self, path: str) -> StreamedResponse:
        from expanse.http.responses.file import Metadata

        def _stream() -> Generator[bytes]:
            yield from self.stream(path)

        response = FileResponse(
            _stream,
            filename=Path(path).name,
            content_disposition="attachment",
        )
        response.metadata = cast("Metadata", self.metadata(path))

        return response
