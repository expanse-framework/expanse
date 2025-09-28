from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from expanse.session.synchronous.stores.store import Store


if TYPE_CHECKING:
    from expanse.http.request import Request


class DictStore(Store):
    def __init__(self, lifetime: int) -> None:
        self._sessions: dict[str, Any] = {}
        self._lifetime = lifetime

    def read(self, session_id: str) -> str:
        if session_id not in self._sessions:
            return ""

        data = self._sessions[session_id]

        expiration = datetime.now(UTC) - timedelta(minutes=self._lifetime)

        if "time" in data and data["time"] >= expiration:
            return data["data"]

        return ""

    def write(self, session_id: str, data: str, request: Request | None = None) -> None:
        self._sessions[session_id] = {
            "time": datetime.now(UTC),
            "data": data,
        }

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def clear(self) -> int:
        expired_ids: list[str] = []

        for session_id, session_data in self._sessions.items():
            if "time" not in session_data:
                continue

            expiration = datetime.now(UTC) - timedelta(minutes=self._lifetime)

            if session_data["time"] < expiration:
                expired_ids.append(session_id)

        for session_id in expired_ids:
            self._sessions.pop(session_id, None)

        return len(expired_ids)
