import os

from collections.abc import AsyncIterable
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import pendulum

from anyio import AsyncFile

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.responses.streamed import StreamedResponse
from expanse.types import Receive
from expanse.types import Send


class FileResponse(StreamedResponse):
    __slots__ = (
        "chunk_size",
        "content_disposition",
        "content_type",
        "filename",
        "path",
        "stat",
    )

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        chunk_size: int = 1024 * 1024,
        filename: str | None = None,
        content_type: str | None = None,
        content_disposition: Literal["attachment", "inline"] = "inline",
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        encoding: str = "utf-8",
    ) -> None:
        self.path: Path = Path(path)
        self.chunk_size: int = chunk_size
        self.filename: str = filename or self.path.name
        self.content_disposition: Literal["attachment", "inline"] = content_disposition
        self.stat: os.stat_result | None = None

        super().__init__(
            self.create_iterator(),
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            encoding=encoding,
        )

    async def create_iterator(self) -> AsyncIterable[bytes]:
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

        stat = self.stat or os.stat(self.path)

        self.headers.set("Content-Length", str(stat.st_size))
        self.headers.set(
            "Last-Modified",
            pendulum.from_timestamp(stat.st_mtime).format(
                "ddd, DD MMM YYYY HH:mm:ss [GMT]"
            ),
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

        async with AsyncFile(self.path.open("rb")) as f:
            return await send(
                {
                    "type": "http.response.body",
                    "body": await f.read(),
                    "more_body": False,
                }
            )
