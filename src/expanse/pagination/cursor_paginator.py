from collections.abc import Iterator
from collections.abc import Sequence
from typing import Self
from typing import TypeVar

from pydantic import BaseModel

from expanse.pagination.cursor import Cursor


_T = TypeVar("_T")


class CursorPaginator[_T]:
    DEFAULT_PER_PAGE: int = 20

    _all_items: Sequence[_T]
    _has_more: bool = False
    _items: Sequence[_T]

    def __init__(
        self,
        items: Sequence[_T],
        *,
        per_page: int | None = None,
        cursor: Cursor | None = None,
        cursor_schema: type[BaseModel] | None = None,
        parameters: Sequence[str] | None = None,
    ) -> None:
        self._per_page: int = per_page or self.DEFAULT_PER_PAGE
        self.set_items(items)
        self._cursor: Cursor | None = cursor
        self._cursor_schema: type[BaseModel] | None = cursor_schema
        self._parameters: Sequence[str] = parameters or []

    def set_items(self, items: Sequence[_T]) -> None:
        self._all_items = items
        self._items = items[: self._per_page]
        self._has_more = len(self._all_items) > len(self._items)

    @property
    def items(self) -> Sequence[_T]:
        return self._items

    @property
    def has_more(self) -> bool:
        return self._has_more

    @property
    def next_cursor(self) -> Cursor | None:
        if (self._cursor is None and not self._has_more) or (
            self._cursor is not None
            and not self._cursor.is_reversed()
            and not self._has_more
        ):
            return None

        if not self._items:
            return None

        return self._get_cursor_for_item(self._items[-1], is_next=True)

    @property
    def previous_cursor(self) -> Cursor | None:
        if self._cursor is None or (self._cursor.is_reversed() and not self._has_more):
            return None

        if not self._items:
            return None

        return self._get_cursor_for_item(self._items[0], is_next=False)

    def _get_cursor_for_item(self, item: _T, is_next: bool) -> Cursor | None:
        return Cursor(
            {
                parameter_name: getattr(item, parameter_name)
                for parameter_name in self._parameters
            },
            reversed=not is_next,
            schema=self._cursor_schema,
        )

    def next(self) -> Self | None:
        if not self.has_more:
            return None

        return self.__class__(
            self._all_items[self._per_page :],
            per_page=self._per_page,
            cursor=self.next_cursor,
            cursor_schema=self._cursor_schema,
            parameters=self._parameters,
        )

    def __iter__(self) -> Iterator[Self]:
        next_: Self | None = self

        while next_:
            yield next_
            next_ = next_.next()
