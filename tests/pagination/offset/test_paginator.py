from expanse.pagination.offset.paginator import Paginator


def test_paginator_initialization() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = Paginator[int](items, per_page=2, total=5)

    assert paginator.items == items[:2]
    assert paginator.total == 5
    assert paginator.current_page == 1
    assert paginator.next_page == 2
    assert paginator.previous_page is None
    assert paginator.first_page == 1
    assert paginator.last_page == 3


def test_paginator_construction_with_page_size_greater_than_items() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = Paginator[int](items, per_page=10, total=5)

    assert paginator.items == items
    assert paginator.total == 5
    assert paginator.current_page == 1
    assert paginator.next_page is None
    assert paginator.previous_page is None
    assert paginator.first_page == 1
    assert paginator.last_page == 1


def test_paginator_multiple_pages() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = Paginator[int](items, per_page=2, total=5)

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


def test_paginator_can_be_iterated() -> None:
    items = [1, 2, 3, 4, 5]
    paginator = Paginator[int](items, per_page=2, total=5)

    collected_items: list[int] = []
    for page in paginator:
        collected_items.extend(page.items)

    assert collected_items == [1, 2, 3, 4, 5]
