from collections.abc import AsyncGenerator
from collections.abc import AsyncIterator
from collections.abc import Buffer
from collections.abc import Iterable
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING
from typing import cast

from expanse.contracts.storage.asynchronous.storage import Storage as StorageContract
from expanse.http.responses.file import FileResponse
from expanse.http.responses.streamed import StreamedResponse


if TYPE_CHECKING:
    from obstore.store import _ObjectStoreMixin


class Storage(StorageContract):
    def __init__(self, store: "_ObjectStoreMixin") -> None:
        self._store: _ObjectStoreMixin = store

    async def get(self, path: str) -> bytes:
        result = await self._store.get_async(path)

        buffer = await result.buffer_async()

        return buffer.to_bytes()

    async def stream(
        self, path: str, chunk_size: int = 10 * 1024 * 1024
    ) -> AsyncIterator[bytes]:
        result = await self._store.get_async(path)

        return result.stream(chunk_size)

    async def put(
        self,
        path: str,
        content: (
            IO[bytes] | Path | bytes | Buffer | Iterator[Buffer] | Iterable[Buffer]
        ),
    ) -> None:
        await self._store.put_async(path, content)

    async def delete(self, path: str) -> None:
        await self._store.delete_async(path)

    async def copy(self, source: str, destination: str) -> None:
        await self._store.copy_async(source, destination)

    async def move(self, source: str, destination: str) -> None:
        await self._store.rename_async(source, destination)

    async def exists(self, path: str) -> bool:
        try:
            await self._store.head_async(path)
            return True
        except FileNotFoundError:
            return False

    async def list(self, prefix: str = "") -> list[str]:
        return [
            meta["path"]
            async for metadata in self._store.list_async(prefix)
            for meta in metadata
        ]

    async def size(self, path: str) -> int:
        metadata = await self._store.head_async(path)

        return metadata["size"]

    async def last_modified(self, path: str) -> datetime:
        metadata = await self._store.head_async(path)

        return metadata["last_modified"]

    async def metadata(self, path: str) -> dict[str, int | datetime | str]:
        metadata = await self._store.head_async(path)

        return {
            "size": metadata["size"],
            "last_modified": metadata["last_modified"],
            "etag": metadata["e_tag"],
        }

    async def as_download(self, path: str) -> StreamedResponse:
        from expanse.http.responses.file import Metadata

        store = self._store

        async def _stream() -> AsyncGenerator[bytes]:
            result = await store.get_async(path)
            async for chunk in result.stream(64 * 1024):
                yield chunk

        response = FileResponse(
            _stream,
            filename=Path(path).name,
            content_disposition="attachment",
        )
        response.metadata = cast("Metadata", await self.metadata(path))

        return response
