from collections.abc import Iterator
from collections.abc import Sequence
from typing import Self
from typing import override

from expanse.pagination.cursor.cursor import Cursor
from expanse.support.adapter import AsyncAdapter
from expanse.support.has_adapter import HasAdapter


class CursorPaginator[T](HasAdapter):
    DEFAULT_PER_PAGE: int = 20

    _all_items: Sequence[T]
    _has_more: bool = False
    _items: Sequence[T]

    def __init__(
        self,
        items: Sequence[T],
        *,
        per_page: int | None = None,
        cursor: Cursor | None = None,
        parameters: Sequence[str] | None = None,
    ) -> None:
        self._per_page: int = per_page or self.DEFAULT_PER_PAGE
        self._cursor: Cursor | None = cursor
        self._parameters: Sequence[str] = parameters or []

        self.set_items(items)

    def set_items(self, items: Sequence[T]) -> None:
        self._all_items = items
        self._items = items[: self._per_page]
        self._has_more = len(self._all_items) > len(self._items)

        # When paginating backwards (reversed cursor), the results are expected to come back
        # in reversed order, so we need to reverse them back
        if self._cursor is not None and self._cursor.is_reversed():
            self._items = list(reversed(self._items))

    @property
    def items(self) -> Sequence[T]:
        return self._items

    @property
    def has_more(self) -> bool:
        return self._has_more

    @property
    def cursor(self) -> Cursor | None:
        return self._cursor

    @property
    def next_cursor(self) -> Cursor | None:
        if not self._items:
            return None

        if (self._cursor is None and not self._has_more) or (
            self._cursor is not None
            and not self._cursor.is_reversed()
            and not self._has_more
        ):
            return None

        return self._get_cursor_for_item(self._items[-1], is_next=True)

    @property
    def next_encoded_cursor(self) -> str | None:
        next_cursor = self.next_cursor
        if next_cursor is None:
            return None

        return next_cursor.encode()

    @property
    def previous_cursor(self) -> Cursor | None:
        if not self._items:
            return None

        if self._cursor is None or (self._cursor.is_reversed() and not self._has_more):
            return None

        return self._get_cursor_for_item(self._items[0], is_next=False)

    @property
    def previous_encoded_cursor(self) -> str | None:
        previous_cursor = self.previous_cursor
        if previous_cursor is None:
            return None

        return previous_cursor.encode()

    def _get_cursor_for_item(self, item: T, is_next: bool) -> Cursor | None:
        return Cursor(
            {
                parameter_name: getattr(item, parameter_name)
                for parameter_name in self._parameters
            },
            reversed=not is_next,
        )

    def next(self) -> Self | None:
        if not self.has_more:
            return None

        return self.__class__(
            self._all_items[self._per_page :],
            per_page=self._per_page,
            cursor=self.next_cursor,
            parameters=self._parameters,
        )

    @override
    @classmethod
    def get_adapter(cls) -> AsyncAdapter[Self]:
        from expanse.pagination.cursor.adapters.envelope import Envelope

        return Envelope()

    def __iter__(self) -> Iterator[Self]:
        next_: Self | None = self

        while next_:
            yield next_
            next_ = next_.next()
