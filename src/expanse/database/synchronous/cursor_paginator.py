from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import Executable
from sqlalchemy.sql.selectable import TypedReturnsRows

from expanse.database.synchronous.session import Session
from expanse.pagination.cursor.cursor import Cursor
from expanse.pagination.cursor.cursor_paginator import (
    CursorPaginator as BaseCursorPaginator,
)


T = TypeVar("T")


class CursorPaginator(BaseCursorPaginator[T]):
    def __init__(
        self,
        items: Sequence[T],
        query: TypedReturnsRows[tuple[T]] | Executable,
        *,
        session: Session,
        per_page: int | None = None,
        cursor: Cursor | None,
        parameters: Sequence[str] | None = None,
    ) -> None:
        super().__init__(
            items,
            per_page=per_page,
            cursor=cursor,
            parameters=parameters,
        )

        self._query: TypedReturnsRows[tuple[T]] | Executable = query
        self._session: Session = session
