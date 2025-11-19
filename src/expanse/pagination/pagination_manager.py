from collections.abc import Callable

from expanse.http.request import Request
from expanse.pagination.cursor.cursor import Cursor


type CursorResolver = Callable[[Request], Cursor | None]
type PageResolver = Callable[[Request], int]


class PaginationManager:
    def __init__(self, request: Request) -> None:
        self._request: Request = request
        self._cursor_resolver: CursorResolver | None = None
        self._page_resolver: PageResolver | None = None

    def resolve_cursor(self) -> Cursor | None:
        if self._cursor_resolver is None:
            return self.default_cursor_resolver(self._request)

        return self._cursor_resolver(self._request)

    def resolve_page(self) -> int:
        if self._page_resolver is None:
            return self.default_page_resolver(self._request)

        return self._page_resolver(self._request)

    def set_cursor_resolver(
        self,
        resolver: CursorResolver,
    ) -> None:
        self._cursor_resolver = resolver

    def set_page_resolver(
        self,
        resolver: PageResolver,
    ) -> None:
        self._page_resolver = resolver

    def default_cursor_resolver(self, request: Request) -> Cursor | None:
        if cursor := request.query_params.get("cursor"):
            return Cursor.decode(cursor)

        return None

    def default_page_resolver(self, request: Request) -> int:
        if page := request.query_params.get("page"):
            try:
                return int(page)
            except ValueError:
                return 1

        return 1


__all__ = ["PaginationManager"]
