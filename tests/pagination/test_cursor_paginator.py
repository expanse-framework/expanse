from expanse.pagination.cursor_paginator import CursorPaginator


def test_cursor_paginator_construction() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=2)

    assert paginator.items == [1, 2]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None


def test_cursor_paginator_construction_with_page_size_greater_than_items() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=10)

    assert paginator.items == [1, 2, 3, 4, 5]
    assert not paginator.has_more
    assert paginator.next_cursor is None
    assert paginator.previous_cursor is None
