import os

from collections.abc import AsyncIterable
from collections.abc import Callable
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal
from typing import NotRequired
from typing import TypedDict
from urllib.parse import quote

import pendulum

from anyio import AsyncFile

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.responses.streamed import StreamedResponse
from expanse.http.responses.streamed import StreamType
from expanse.types import Receive
from expanse.types import Send


class Metadata(TypedDict, total=False):
    size: NotRequired[int]
    last_modified: NotRequired[datetime]


class FileResponse(StreamedResponse):
    __slots__ = (
        "chunk_size",
        "content_disposition",
        "content_type",
        "filename",
        "metadata",
        "path",
    )

    def __init__(
        self,
        path: (
            str
            | os.PathLike[str]
            | StreamType[bytes | str]
            | Callable[[], StreamType[bytes | str]]
        ),
        *,
        chunk_size: int = 1024 * 1024,
        filename: str | None = None,
        content_type: str | None = None,
        content_disposition: Literal["attachment", "inline"] = "inline",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self.path: (
            Path | StreamType[bytes | str] | Callable[[], StreamType[bytes | str]]
        ) = Path(path) if isinstance(path, (str, os.PathLike)) else path
        self.chunk_size: int = chunk_size
        self.filename: str = filename or (
            self.path.name if isinstance(self.path, Path) else "file"
        )
        self.content_disposition: Literal["attachment", "inline"] = content_disposition
        self.metadata: Metadata = {}

        super().__init__(
            self.create_iterator() if isinstance(self.path, Path) else self.path,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            encoding=encoding,
        )

    async def create_iterator(self) -> AsyncIterable[bytes]:
        assert isinstance(self.path, Path), "Path must be a pathlib.Path instance"

        async with AsyncFile(self.path.open("rb")) as file:
            while chunk := await file.read(self.chunk_size):
                yield chunk

    async def prepare(self, request: Request, container: Container) -> None:
        if not self.content_type:
            from mimetypes import guess_type

            content_type, encoding = guess_type(self.filename or self.path.name)

            if content_type is None:
                content_type = "application/octet-stream"

            self.headers["Content-Type"] = content_type

            if encoding is not None:
                self.headers["Content-Encoding"] = encoding

        size: int | None = self.metadata.get("size") or (
            os.stat(self.path).st_size if isinstance(self.path, Path) else None
        )
        last_modified: pendulum.DateTime | None = None

        if "last_modified" in self.metadata:
            if isinstance(self.metadata["last_modified"], datetime):
                last_modified = pendulum.instance(self.metadata["last_modified"])
            else:
                last_modified = pendulum.from_timestamp(self.metadata["last_modified"])
        elif isinstance(self.path, Path):
            last_modified = pendulum.from_timestamp(os.stat(self.path).st_mtime)

        if size is not None:
            self.headers.set("Content-Length", str(size))
        if last_modified is not None:
            self.headers.set(
                "Last-Modified",
                last_modified.format("ddd, DD MMM YYYY HH:mm:ss [GMT]"),
            )
        else:
            self.headers.set(
                "Last-Modified",
                pendulum.now().format("ddd, DD MMM YYYY HH:mm:ss [GMT]"),
            )

        filename = quote(self.filename)

        if filename == self.filename:
            self.headers.set(
                "Content-Disposition",
                f'{self.content_disposition}; filename="{self.filename}"',
            )
        else:
            self.headers.set(
                "Content-Disposition",
                f"{self.content_disposition}; filename*=UTF-8''{filename}",
            )

        # TODO: Etag

        await super().prepare(request, container)

    async def send_body(self, send: Send, receive: Receive) -> None:
        if self.chunk_size < int(self.headers["Content-Length"]):
            return await super().send_body(send, receive)

        if isinstance(self.path, Path):
            async with AsyncFile(self.path.open("rb")) as f:
                return await send(
                    {
                        "type": "http.response.body",
                        "body": await f.read(),
                        "more_body": False,
                    }
                )
        else:
            return await super().send_body(send, receive)
