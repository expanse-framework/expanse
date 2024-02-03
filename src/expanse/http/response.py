from __future__ import annotations

import json
import os
import stat

from mimetypes import guess_type
from typing import TYPE_CHECKING
from typing import Any
from typing import Mapping
from typing import NoReturn
from typing import Self
from urllib.parse import quote

import anyio
import pendulum

from starlette.responses import Response as BaseResponse

from expanse.foundation.http.exceptions import HTTPException
from expanse.support._compat import md5_hexdigest


if TYPE_CHECKING:
    from os import PathLike

    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Response(BaseResponse):
    @classmethod
    def json(
        cls,
        content: Any = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> Self:
        content = json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

        return cls(
            content,
            media_type="application/json",
            status_code=status_code,
            headers=headers,
        )

    @classmethod
    def text(
        cls,
        content: Any = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> Self:
        return cls(
            content,
            media_type="text/plain",
            status_code=status_code,
            headers=headers,
        )

    @classmethod
    def file(
        cls,
        path: str | PathLike[str],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
    ) -> FileResponse:
        return FileResponse(
            path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            filename=filename,
        )

    @classmethod
    def abort(
        cls,
        status_code: int,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> NoReturn:
        raise HTTPException(status_code, detail=message, headers=headers)


class FileResponse(Response):
    chunk_size = 64 * 1024

    def __init__(
        self,
        path: str | PathLike[str],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        stat_result: os.stat_result | None = None,
        method: str | None = None,
        content_disposition_type: str = "attachment",
    ) -> None:
        self.path = path
        self.status_code = status_code
        self.filename = filename
        self.send_header_only = method is not None and method.upper() == "HEAD"
        if media_type is None:
            media_type = guess_type(filename or path)[0] or "text/plain"
        self.media_type = media_type
        self.init_headers(headers)
        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            if content_disposition_filename != self.filename:
                content_disposition = "{}; filename*=utf-8''{}".format(
                    content_disposition_type, content_disposition_filename
                )
            else:
                content_disposition = '{}; filename="{}"'.format(
                    content_disposition_type, self.filename
                )
            self.headers.setdefault("content-disposition", content_disposition)

    def set_stat_headers(self, stat_result: os.stat_result) -> None:
        content_length = str(stat_result.st_size)
        last_modified = (
            pendulum.from_timestamp(stat_result.st_mtime)
            .to_rfc2822_string()
            .replace("+0000", "GMT")
        )
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = md5_hexdigest(etag_base.encode(), usedforsecurity=False)

        self.headers.setdefault("content-length", content_length)
        self.headers.setdefault("last-modified", last_modified)
        self.headers.setdefault("etag", etag)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            stat_result = await anyio.to_thread.run_sync(os.stat, self.path)
            self.set_stat_headers(stat_result)
        except FileNotFoundError:
            raise RuntimeError(f"File at path {self.path} does not exist.")
        else:
            mode = stat_result.st_mode
            if not stat.S_ISREG(mode):
                raise RuntimeError(f"File at path {self.path} is not a file.")
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        if self.send_header_only:
            await send({"type": "http.response.body", "body": b"", "more_body": False})
        else:
            async with await anyio.open_file(self.path, mode="rb") as file:
                more_body = True
                while more_body:
                    chunk = await file.read(self.chunk_size)
                    more_body = len(chunk) == self.chunk_size
                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": more_body,
                        }
                    )
