import time

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import filelock

from expanse.http.request import Request
from expanse.session.synchronous.stores.store import Store


class FileStore(Store):
    def __init__(self, path: Path, lifetime: int) -> None:
        self._path = path
        self._lifetime = lifetime

    def read(self, session_id: str) -> str:
        if not self._path.exists():
            return ""

        if (
            not self._path.joinpath(session_id).exists()
            or not self._path.joinpath(session_id).is_file()
        ):
            return ""

        if (
            self._path.joinpath(session_id).stat().st_mtime + self._lifetime * 60
            <= time.time()
        ):
            return ""

        with self._lock(session_id):
            data = self._path.joinpath(session_id).read_text()

            return data

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        if not self._path.exists():
            self._path.mkdir(parents=True, exist_ok=True)

        with self._lock(session_id):
            self._path.joinpath(session_id).write_text(data)

    def delete(self, session_id: str) -> None:
        with self._lock(session_id):
            self._path.joinpath(session_id).unlink(missing_ok=True)

    def clear(self) -> int:
        count = 0

        for path in self._path.glob("*"):
            if path.stat().st_mtime + self._lifetime * 60 <= time.time():
                path.unlink(missing_ok=True)

                if path.suffix == ".lock":
                    continue

                count += 1

        return count

    @contextmanager
    def _lock(self, session_id: str) -> Iterator[None]:
        lock_path = self._path.joinpath(session_id).with_suffix(".lock")

        with filelock.FileLock(lock_path):
            yield
