from expanse.pagination.cursor.cursor_paginator import CursorPaginator


def test_cursor_paginator_construction() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=2)

    assert paginator.items == [1, 2]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None
    assert paginator.next_encoded_cursor is not None
    assert paginator.previous_encoded_cursor is None


def test_cursor_paginator_construction_with_page_size_greater_than_items() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=10)

    assert paginator.items == [1, 2, 3, 4, 5]
    assert not paginator.has_more
    assert paginator.next_cursor is None
    assert paginator.previous_cursor is None
    assert paginator.next_encoded_cursor is None
    assert paginator.previous_encoded_cursor is None


def test_cursor_paginator_empty_items() -> None:
    items: list[int] = []
    paginator = CursorPaginator[int](items, per_page=2)

    assert paginator.items == []
    assert not paginator.has_more
    assert paginator.next_cursor is None
    assert paginator.previous_cursor is None
    assert paginator.next_encoded_cursor is None
    assert paginator.previous_encoded_cursor is None


def test_cursor_paginator_multiple_pages() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=2)

    assert paginator.items == [1, 2]
    assert paginator.has_more

    paginator2 = paginator.next()

    assert paginator2 is not None
    assert paginator2.items == [3, 4]
    assert paginator2.has_more

    paginator3 = paginator2.next()
    assert paginator3 is not None
    assert paginator3.items == [5]
    assert not paginator3.has_more

    paginator4 = paginator3.next()
    assert paginator4 is None


def test_cursor_paginator_can_be_iterated() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = CursorPaginator[int](items, per_page=2)

    collected_items: list[int] = []
    for page in paginator:
        collected_items.extend(page.items)

    assert collected_items == [1, 2, 3, 4, 5]
