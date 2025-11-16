from collections.abc import Callable

from expanse.http.request import Request
from expanse.pagination.cursor import Cursor


type CursorResolver = Callable[[Request], Cursor | None]


class PaginationManager:
    def __init__(self, request: Request) -> None:
        self._request = request
        self._cursor_resolver: CursorResolver | None = None

    def resolve_cursor(self) -> Cursor | None:
        if self._cursor_resolver is None:
            return self.default_cursor_resolver(self._request)

        return self._cursor_resolver(self._request)

    def set_cursor_resolver(
        self,
        resolver: CursorResolver,
    ) -> None:
        self._cursor_resolver = resolver

    def default_cursor_resolver(self, request: Request) -> Cursor | None:
        if cursor := request.query_params.get("cursor"):
            return Cursor.decode(cursor)

        return None


__all__ = ["PaginationManager"]
