from __future__ import annotations

from typing import Any


_NOT_FOUND = object()


class Config:
    def __init__(self, config: dict) -> None:
        self._config = config

    def get(self, key: str | None = None, default: Any = None) -> Any:
        config: dict[str, Any] = self._config

        if not key:
            return config

        parts = key.split(".")
        for part in parts:
            if part not in config:
                return default

            config = config[part]

        return config

    def __setitem__(self, item: Any, value: Any) -> Any:
        config: dict[str, Any] = self._config

        parts = item.split(".")
        count = len(parts)
        for i, part in enumerate(parts):
            if i == count - 1:
                config[part] = value
                return

            if part not in config:
                config[part] = {}

            config = config[part]

    def __getitem__(self, item: Any) -> Any:
        value = self.get(item, default=_NOT_FOUND)

        if value is _NOT_FOUND:
            raise KeyError(item)

        return value

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._config!r})"
