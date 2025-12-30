from collections.abc import Generator
from typing import TYPE_CHECKING
from typing import NamedTuple

import pytest
import sqlalchemy as sa

from expanse.configuration.config import Config
from expanse.core.application import Application
from expanse.database.pagination.exceptions import DatabasePaginationError
from expanse.database.synchronous.database_manager import DatabaseManager
from expanse.database.synchronous.session import Session
from expanse.pagination.cursor.cursor import Cursor


if TYPE_CHECKING:
    from expanse.pagination.cursor.cursor_paginator import CursorPaginator
    from expanse.pagination.offset.paginator import Paginator


class UserRow(NamedTuple):
    id: int
    first_name: str
    last_name: str
    email: str


class AliasedUserRow(NamedTuple):
    foo: int
    first_name: str


@pytest.fixture()
def session() -> Generator[Session]:
    app = Application()
    app.set_config(
        Config(
            {
                "database": {
                    "default": "sqlite",
                    "connections": {
                        "sqlite": {"driver": "sqlite", "database": ":memory:"},
                    },
                }
            }
        )
    )

    db = DatabaseManager(app)

    with db.session() as session:
        session.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR,
            email VARCHAR NOT NULL
        )
        """)

        session.execute("""
        INSERT INTO users (first_name, last_name, email) VALUES
            ('John', 'Doe', 'john@doe.com'),
            ('Jane', 'Smith', 'jane@smith.com'),
            ('Alice', 'Johnson', 'alice@johnson.com'),
            ('Jane', 'Doe', 'jane@doe.com')
        """)

        yield session


def test_cursor_paginate(session: Session) -> None:
    paginator: CursorPaginator[UserRow] = session.cursor_paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id")),
        per_page=2,
    )

    assert paginator.items == [
        (1, "John", "Doe", "john@doe.com"),
        (2, "Jane", "Smith", "jane@smith.com"),
    ]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None
    assert paginator.next_cursor.parameter("id") == 2


def test_cursor_paginate_descending_order(session: Session) -> None:
    paginator: CursorPaginator[UserRow] = session.cursor_paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id").desc()),
        per_page=2,
    )

    assert paginator.items == [
        (4, "Jane", "Doe", "jane@doe.com"),
        (3, "Alice", "Johnson", "alice@johnson.com"),
    ]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None
    assert paginator.next_cursor.parameter("id") == 3


def test_cursor_paginate_aliased_column(session: Session) -> None:
    paginator: CursorPaginator[AliasedUserRow] = session.cursor_paginate(
        sa.select(sa.column("id").label("foo"), sa.column("first_name"))
        .select_from(sa.table("users"))
        .order_by(sa.column("id").label("foo")),
        per_page=2,
    )

    assert paginator.items == [
        AliasedUserRow(foo=1, first_name="John"),
        AliasedUserRow(foo=2, first_name="Jane"),
    ]
    assert paginator.items[0].foo == 1
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None
    assert paginator.next_cursor.parameter("foo") == 2


def test_cursor_paginate_aliased_column_descending_order(session: Session) -> None:
    paginator: CursorPaginator[AliasedUserRow] = session.cursor_paginate(
        sa.select(sa.column("id").label("foo"), sa.column("first_name"))
        .select_from(sa.table("users"))
        .order_by(sa.column("id").label("foo").desc()),
        per_page=2,
    )

    assert paginator.items == [(4, "Jane"), (3, "Alice")]
    assert paginator.items[0].foo == 4
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.next_cursor.parameter("foo") == 3


def test_cursor_paginate_order_by_multiple_columns(session: Session) -> None:
    paginator: CursorPaginator[UserRow] = session.cursor_paginate(
        sa.select("*")
        .select_from(sa.table("users"))
        .order_by(sa.column("first_name").desc(), sa.column("id").desc()),
        per_page=3,
    )

    assert paginator.items == [
        (1, "John", "Doe", "john@doe.com"),
        (4, "Jane", "Doe", "jane@doe.com"),
        (2, "Jane", "Smith", "jane@smith.com"),
    ]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.previous_cursor is None
    assert paginator.next_cursor.parameter("id") == 2
    assert paginator.next_cursor.parameter("first_name") == "Jane"


def test_cursor_paginate_with_a_cursor(session: Session) -> None:
    paginator: CursorPaginator[UserRow] = session.cursor_paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id").desc()),
        per_page=2,
        cursor=Cursor({"id": 3}),
    )

    assert paginator.items == [
        (2, "Jane", "Smith", "jane@smith.com"),
        (1, "John", "Doe", "john@doe.com"),
    ]
    assert not paginator.has_more
    assert paginator.next_cursor is None
    assert paginator.previous_cursor is not None
    assert paginator.previous_cursor.parameter("id") == 2


def test_cursor_paginate_with_a_reversed_cursor(session: Session) -> None:
    paginator: CursorPaginator[UserRow] = session.cursor_paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id").desc()),
        per_page=2,
        cursor=Cursor({"id": 1}, reversed=True),
    )

    assert paginator.items == [
        (3, "Alice", "Johnson", "alice@johnson.com"),
        (2, "Jane", "Smith", "jane@smith.com"),
    ]
    assert paginator.has_more
    assert paginator.next_cursor is not None
    assert paginator.next_cursor.parameter("id") == 2
    assert paginator.previous_cursor is not None
    assert paginator.previous_cursor.parameter("id") == 3


def test_cursor_paginate_without_order_by_raise_an_error(session: Session) -> None:
    with pytest.raises(DatabasePaginationError):
        session.cursor_paginate(
            sa.select("*").select_from(sa.table("users")),
            per_page=2,
        )


def test_paginate_with_empty_result_set(session: Session) -> None:
    paginator: Paginator[UserRow] = session.paginate(
        sa.select("*")
        .select_from(sa.table("users"))
        .where(sa.column("id") > 100)
        .order_by(sa.column("id")),
        per_page=2,
    )

    assert paginator.items == []
    assert not paginator.has_more
    assert paginator.first_page == 1
    assert paginator.current_page == 1
    assert paginator.last_page == 0
    assert paginator.next_page is None
    assert paginator.previous_page is None
    assert paginator.total == 0


def test_paginate_first_page(session: Session) -> None:
    paginator: Paginator[UserRow] = session.paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id")),
        per_page=2,
    )

    assert paginator.items == [
        (1, "John", "Doe", "john@doe.com"),
        (2, "Jane", "Smith", "jane@smith.com"),
    ]
    assert paginator.first_page == 1
    assert paginator.current_page == 1
    assert paginator.last_page == 2
    assert paginator.next_page == 2
    assert paginator.previous_page is None
    assert paginator.total == 4


def test_paginate_second_page(session: Session) -> None:
    paginator: Paginator[UserRow] = session.paginate(
        sa.select("*").select_from(sa.table("users")).order_by(sa.column("id")),
        per_page=2,
        page=2,
    )

    assert paginator.items == [
        (3, "Alice", "Johnson", "alice@johnson.com"),
        (4, "Jane", "Doe", "jane@doe.com"),
    ]
    assert paginator.first_page == 1
    assert paginator.current_page == 2
    assert paginator.last_page == 2
    assert paginator.next_page is None
    assert paginator.previous_page == 1
    assert paginator.total == 4
