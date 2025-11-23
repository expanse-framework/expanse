from collections.abc import Iterator
from collections.abc import Sequence
from typing import Self
from typing import override

from expanse.support.adapter import AsyncAdapter
from expanse.support.has_adapter import HasAdapter


class Paginator[T](HasAdapter):
    DEFAULT_PER_PAGE: int = 20

    _all_items: Sequence[T]
    _has_more: bool = False
    _items: Sequence[T]

    def __init__(
        self,
        items: Sequence[T],
        *,
        total: int,
        per_page: int | None = None,
        current_page: int | None = None,
    ) -> None:
        self._per_page: int = per_page or self.DEFAULT_PER_PAGE
        self._total: int = total
        self.set_items(items)
        self._current_page: int | None = current_page

    def set_items(self, items: Sequence[T]) -> None:
        self._all_items = items
        self._items = items[: self._per_page]
        self._has_more = len(self._all_items) > self._per_page

    @property
    def items(self) -> Sequence[T]:
        return self._items

    @property
    def has_more(self) -> bool:
        return self._has_more

    @property
    def current_page(self) -> int:
        if self._current_page is None:
            return 1

        return self._current_page if self._current_page > 0 else 1

    @property
    def next_page(self) -> int | None:
        if not self.has_more:
            return None

        return self.current_page + 1

    @property
    def previous_page(self) -> int | None:
        if self.current_page <= 1:
            return None

        return self.current_page - 1

    @property
    def first_page(self) -> int:
        return 1

    @property
    def last_page(self) -> int:
        return (self._total + self._per_page - 1) // self._per_page

    @property
    def total(self) -> int:
        return self._total

    def next(self) -> Self | None:
        if not self.has_more:
            return None

        return self.__class__(
            self._all_items[self._per_page :],
            total=self._total,
            per_page=self._per_page,
            current_page=self.next_page,
        )

    @override
    @classmethod
    def get_adapter(cls) -> AsyncAdapter[Self]:
        from expanse.pagination.offset.adapters.envelope import Envelope

        return Envelope()

    def __iter__(self) -> Iterator[Self]:
        next_: Self | None = self

        while next_:
            yield next_
            next_ = next_.next()
