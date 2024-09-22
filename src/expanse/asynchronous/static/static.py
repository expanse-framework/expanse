import os

from pathlib import Path
from typing import Self

from expanse.asynchronous.http.helpers import abort
from expanse.asynchronous.http.helpers import respond
from expanse.asynchronous.http.response import Response


class Static:
    def __init__(
        self, directories: list[Path], prefix: str, url: str | None = None
    ) -> None:
        self._directories = directories
        self._prefix: str = prefix.rstrip("/")
        self._url: str | None = url.rstrip("/") if url is not None else None

    async def get(self, path: str) -> Response:
        full_path = self._find(path)

        if not full_path:
            await abort(404)

        return await (await respond()).file(str(full_path))

    def url(self, path: str) -> str:
        static_url = []

        if self._url is not None:
            static_url.append(self._url)
            if self._prefix.lstrip("/"):
                static_url.append(self._prefix.lstrip("/"))
        elif self._prefix:
            static_url.append(self._prefix)

        static_url.append(path)

        return "/".join(static_url)

    def add_path(self, *paths: Path) -> Self:
        self._directories.extend(paths)

        return self

    def _find(self, path: str) -> Path | None:
        for directory in self._directories:
            directory_path = directory.joinpath(path).resolve()

            if os.path.commonpath([str(directory_path), str(directory)]) != str(
                directory
            ):
                continue

            if not directory_path.exists():
                continue

            return directory_path
