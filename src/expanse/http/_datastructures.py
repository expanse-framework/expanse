import os

from collections.abc import Iterable
from collections.abc import Mapping
from tempfile import SpooledTemporaryFile
from typing import Any
from typing import NamedTuple
from urllib.parse import parse_qsl
from urllib.parse import urlencode

from expanse.http.cookie import Cookie
from expanse.http.header_bag import HeaderBag
from expanse.support._concurrency import run_in_threadpool
from expanse.support._datastructures import MultiMapping


class ContentType:
    __slots__ = ("options", "type")

    def __init__(self, type: str, options: dict[str, str]) -> None:
        self.type, self.options = type, options

    @classmethod
    def from_string(cls, content_type_raw_line: str) -> "ContentType":
        """
        Create a ContentType instance from a raw content type string.

        :param content_type_raw_line: The raw content type string.
        :return: An instance of ContentType.
        """
        parts = content_type_raw_line.split(";")
        type = parts[0].strip()
        options = {}

        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                options[key.strip()] = value.strip()
            else:
                options[part.strip()] = ""

        return cls(type, options)

    def __repr__(self) -> str:
        return f"<{self.__class__.__qualname__}: {self}>"

    def __str__(self) -> str:
        return self.type + "".join(f"; {k}={v}" for k, v in self.options.items())

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, str):
            return NotImplemented
        return self.type == other


class QueryParams(MultiMapping[str, str]):
    """
    An immutable MutableMultiMapping.
    """

    __slots__ = ("_dict", "_list")

    def __init__(
        self,
        raw: MultiMapping[str, str]
        | Mapping[str, str]
        | Iterable[tuple[str, str]]
        | str
        | bytes
        | None = None,
    ) -> None:
        if isinstance(raw, str):
            super().__init__(parse_qsl(raw, keep_blank_values=True))
        elif isinstance(raw, bytes):
            super().__init__(parse_qsl(raw.decode("latin-1"), keep_blank_values=True))
        else:
            super().__init__(raw)

    def __str__(self) -> str:
        return urlencode(self._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"


class CookieJar(MultiMapping[str, Cookie]):
    """
    An immutable MutableMultiMapping for cookies.
    """

    __slots__ = ("_dict", "_list")

    def __init__(
        self,
        raw: MultiMapping[str, Cookie]
        | Mapping[str, Cookie]
        | Iterable[tuple[str, Cookie]]
        | None = None,
    ) -> None:
        super().__init__(raw or {})


class Address(NamedTuple):
    host: str | None
    port: int | None


class UploadFile:
    """
    An uploaded file included as part of the request data.
    """

    __slots__ = ("content_type", "file", "filename", "headers")

    spool_max_size: int = 1024 * 1024

    def __init__(self, filename: str, headers: HeaderBag) -> None:
        self.filename: str = filename
        self.headers: HeaderBag = headers
        self.content_type: str = headers.get("content-type", "")
        self.file = SpooledTemporaryFile(max_size=self.spool_max_size, mode="w+b")  # noqa: SIM115

    @property
    def in_memory(self) -> bool:
        rolled_to_disk = getattr(self.file, "_rolled", True)
        return not rolled_to_disk

    def write(self, data: bytes) -> None:
        self.file.write(data)

    async def awrite(self, data: bytes) -> None:
        if self.in_memory:
            self.write(data)
        else:
            await run_in_threadpool(self.write, data)

    def read(self, size: int = -1) -> bytes:
        return self.file.read(size)

    async def aread(self, size: int = -1) -> bytes:
        if self.in_memory:
            return self.read(size)
        return await run_in_threadpool(self.read, size)

    def seek(self, offset: int) -> None:
        self.file.seek(offset)

    async def aseek(self, offset: int) -> None:
        if self.in_memory:
            self.seek(offset)
        else:
            await run_in_threadpool(self.seek, offset)

    def close(self) -> None:
        self.file.close()

    async def aclose(self) -> None:
        if self.in_memory:
            self.close()
        else:
            await run_in_threadpool(self.close)

    def save(self, filepath: str) -> None:
        """
        Save file to disk.
        """
        copy_bufsize = 1024 * 1024 if os.name == "nt" else 64 * 1024
        file_position = self.file.tell()
        self.file.seek(0, 0)
        try:
            with open(filepath, "wb+") as target_file:
                source_read = self.file.read
                target_write = target_file.write
                while True:
                    buf = source_read(copy_bufsize)
                    if not buf:
                        break
                    target_write(buf)
        finally:
            self.file.seek(file_position)

    async def asave(self, filepath: str) -> None:
        """
        Save file to disk, work in threading pool.
        """
        await run_in_threadpool(self.save, filepath)


class FormData(MultiMapping[str, str | UploadFile]):
    """
    An immutable MultiMapping, containing both file uploads and text input.
    """

    __slots__ = MultiMapping.__slots__

    def close(self) -> None:
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                value.close()

    async def aclose(self) -> None:
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.aclose()
