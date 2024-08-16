from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Any


class View:
    def __init__(
        self,
        identifier: str,
        data: Mapping[Any, Any] | None = None,
        status_code: int = 200,
        headers: MutableMapping[str, Any] | None = None,
    ) -> None:
        self._identifier = identifier
        self._data = data or {}
        self._status_code = status_code
        self._headers = headers

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def data(self) -> Mapping[Any, Any]:
        return self._data

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> MutableMapping[str, Any] | None:
        return self._headers
