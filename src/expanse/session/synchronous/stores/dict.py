from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.session.synchronous.stores.store import Store


if TYPE_CHECKING:
    from expanse.http.request import Request


class DictStore(Store):
    def __init__(self) -> None:
        self._sessions: dict[str, str] = {}

    def read(self, session_id: str) -> str:
        return self._sessions.get(session_id, "{}")

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        self._sessions[session_id] = data

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
