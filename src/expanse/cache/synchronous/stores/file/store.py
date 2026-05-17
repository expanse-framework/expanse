from __future__ import annotations

import hashlib
import pickle
import time

from typing import TYPE_CHECKING
from typing import Any
from typing import override

from expanse.contracts.cache.synchronous.store import Store


if TYPE_CHECKING:
    from pathlib import Path


class FileStore(Store):
    def __init__(self, path: Path, permissions: int | None = None) -> None:
        self._path: Path = path
        self._permissions: int | None = permissions

        if not self._path.exists():
            self._path.mkdir(
                mode=self._permissions or 0o777, parents=True, exist_ok=True
            )

    @override
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        path = self._path_for_key(key, mkdir=True)
        value = pickle.dumps(value)

        expiration = int(time.time()) + ttl if ttl is not None else 0

        result = path.write_text(f"{expiration}\n{value.hex()}")

        if result > 0:
            self._ensure_permissions(path)

            return True

        return False

    @override
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        results: list[bool] = []
        for key, value in items.items():
            result = self.set(key, value, ttl)
            results.append(result)

        return all(results)

    @override
    def get(self, key: str) -> Any | None:
        path = self._path_for_key(key)

        if not path.exists():
            return None

        content = path.read_text()
        expiration_str, value_hex = content.split("\n", 1)
        expiration = int(expiration_str)

        if expiration != 0 and expiration < int(time.time()):
            path.unlink()

            return None

        return pickle.loads(bytes.fromhex(value_hex))

    @override
    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        if not keys:
            return {}

        return {key: self.get(key) for key in keys}

    @override
    def has(self, key: str) -> bool:
        return self.get(key) is not None

    @override
    def delete(self, key: str) -> bool:
        path = self._path_for_key(key)
        if path.exists():
            path.unlink()

            return True

        return False

    @override
    def clear(self) -> bool:
        for path in self._path.rglob("*"):
            if path.is_file():
                path.unlink()

        return True

    def _path_for_key(self, key: str, mkdir: bool = False) -> Path:
        hash = hashlib.sha1(key.encode()).hexdigest()
        path = self._path.joinpath(hash[:2], hash[2:4], hash[4:])

        if not path.parent.exists() and mkdir:
            path.parent.mkdir(
                mode=self._permissions or 0o777, parents=True, exist_ok=True
            )

        return path

    def _ensure_permissions(self, path: Path) -> bool:
        if (
            self._permissions is None
            or path.stat().st_mode & 0o777 == self._permissions
        ):
            return True

        path.chmod(self._permissions)

        return True
