from typing import Any


class Context:
    """
    The `Context` class can be used to track and store any relevant information
    during the execution of a request or a command for instance.
    """

    def __init__(self):
        self._data: dict[str, Any] = {}

    def has(self, key: str) -> bool:
        return key in self._data

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data
