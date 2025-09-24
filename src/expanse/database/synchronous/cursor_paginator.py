from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import Query

from expanse.database.synchronous.session import Session
from expanse.pagination.cursor import Cursor
from expanse.pagination.cursor_paginator import CursorPaginator as BaseCursorPaginator


T = TypeVar("T")


class CursorPaginator(BaseCursorPaginator[T]):
    def __init__(
        self,
        items: Sequence[T],
        query: Query | Select,
        *,
        session: Session | None = None,
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

        self._query: Query[T] | Select = query
        self._session: Session | None = session
