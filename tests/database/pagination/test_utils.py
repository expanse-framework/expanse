from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import select
from sqlalchemy import table
from sqlalchemy.sql import column

from expanse.database.pagination.utils import prepare_pagination
from expanse.pagination.cursor.cursor import Cursor


TABLE = table(
    "users",
    column("id", Integer()),
    column("name", String()),
    column("created_at", DateTime(timezone=True)),
)


def test_prepare_pagination_with_default_parameters() -> None:
    query = TABLE.select().order_by(TABLE.c.id)
    prepared, parameters, cursor = prepare_pagination(query, 10)

    assert (
        prepared.compile().string.replace("\n", "")
        == "SELECT users.id, users.name, users.created_at FROM users ORDER BY users.id LIMIT :param_1"
    )
    assert prepared.compile().params == {"param_1": 11}
    assert parameters == ["id"]
    assert cursor is None


def test_prepare_pagination_with_multiple_columns() -> None:
    query = TABLE.select().order_by(TABLE.c.id, TABLE.c.created_at)
    prepared, parameters, cursor = prepare_pagination(query, 10)

    assert (
        prepared.compile().string.replace("\n", "")
        == "SELECT users.id, users.name, users.created_at FROM users ORDER BY users.id, users.created_at LIMIT :param_1"
    )
    assert prepared.compile().params == {"param_1": 11}
    assert parameters == ["id", "created_at"]
    assert cursor is None


def test_prepare_pagination_with_multiple_columns_descending_order() -> None:
    query = TABLE.select().order_by(TABLE.c.id.desc(), TABLE.c.created_at.desc())
    prepared, parameters, cursor = prepare_pagination(query, 10)

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "ORDER BY users.id DESC, users.created_at DESC "
        "LIMIT :param_1"
    )
    assert prepared.compile().params == {"param_1": 11}
    assert parameters == ["id", "created_at"]
    assert cursor is None


def test_prepare_pagination_with_cursor_and_descending_order() -> None:
    query = TABLE.select().order_by(TABLE.c.id.desc())
    prepared, parameters, cursor = prepare_pagination(
        query, 10, cursor=Cursor({"id": 42})
    )

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE (users.id) < (:param_1) "
        "ORDER BY users.id DESC "
        "LIMIT :param_2"
    )
    assert prepared.compile().params == {"param_2": 11, "param_1": 42}
    assert parameters == ["id"]
    assert cursor is not None
    assert cursor.parameters == {"id": 42}


def test_prepare_pagination_with_cursor_and_ascending_order() -> None:
    query = TABLE.select().order_by(TABLE.c.id.asc())
    prepared, parameters, cursor = prepare_pagination(
        query, 10, cursor=Cursor({"id": 42})
    )

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE (users.id) > (:param_1) "
        "ORDER BY users.id ASC "
        "LIMIT :param_2"
    )
    assert prepared.compile().params == {"param_2": 11, "param_1": 42}
    assert parameters == ["id"]
    assert cursor is not None
    assert cursor.parameters == {"id": 42}


def test_prepare_pagination_with_cursor_and_multiple_order_columns() -> None:
    query = TABLE.select().order_by(TABLE.c.id.desc(), TABLE.c.created_at.desc())
    prepared, parameters, cursor = prepare_pagination(
        query,
        10,
        cursor=Cursor(
            {"id": 42, "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z")}
        ),
    )

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE (users.id, users.created_at) < (:param_1, :param_2) "
        "ORDER BY users.id DESC, users.created_at DESC "
        "LIMIT :param_3"
    )
    assert prepared.compile().params == {
        "param_3": 11,
        "param_1": 42,
        "param_2": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }
    assert parameters == ["id", "created_at"]
    assert cursor is not None
    assert cursor.parameters == {
        "id": 42,
        "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }


def test_prepare_pagination_with_cursor_and_aliased_column() -> None:
    query = select(TABLE.c.id.label("user_id")).order_by(
        TABLE.c.id.label("user_id").desc()
    )
    prepared, parameters, cursor = prepare_pagination(
        query, 10, cursor=Cursor({"user_id": 42})
    )

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id AS user_id "
        "FROM users "
        "WHERE (users.id) < (:param_1) "
        "ORDER BY user_id DESC "
        "LIMIT :param_2"
    )
    assert prepared.compile().params == {"param_2": 11, "param_1": 42}
    assert parameters == ["user_id"]
    assert cursor is not None
    assert cursor.parameters == {"user_id": 42}


def test_prepare_pagination_with_reversed_cursor_and_multiple_order_columns() -> None:
    query = TABLE.select().order_by(TABLE.c.id.desc(), TABLE.c.created_at.desc())
    prepared, parameters, cursor = prepare_pagination(
        query,
        10,
        cursor=Cursor(
            {"id": 42, "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z")},
            reversed=True,
        ),
    )

    assert prepared.compile().string.replace("\n", "") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE (users.id, users.created_at) > (:param_1, :param_2) "
        "ORDER BY users.id ASC, users.created_at ASC "
        "LIMIT :param_3"
    )
    assert prepared.compile().params == {
        "param_3": 11,
        "param_1": 42,
        "param_2": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }
    assert parameters == ["id", "created_at"]
    assert cursor is not None
    assert cursor.parameters == {
        "id": 42,
        "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }


def test_prepare_pagination_with_two_columns_and_different_directions() -> None:
    query = TABLE.select().order_by(TABLE.c.id.desc(), TABLE.c.created_at.asc())
    prepared, parameters, cursor = prepare_pagination(
        query,
        10,
        cursor=Cursor(
            {
                "id": 42,
                "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
            }
        ),
    )

    assert prepared.compile().string.replace("\n", "").replace("  ", " ") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE users.id < :id_1 OR users.id = :id_2 AND users.created_at > :created_at_1 "
        "ORDER BY users.id DESC, users.created_at ASC "
        "LIMIT :param_1"
    )
    assert prepared.compile().params == {
        "param_1": 11,
        "id_1": 42,
        "id_2": 42,
        "created_at_1": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }
    assert parameters == ["id", "created_at"]
    assert cursor is not None
    assert cursor.parameters == {
        "id": 42,
        "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
    }


def test_prepare_pagination_with_multiple_columns_and_different_directions() -> None:
    query = TABLE.select().order_by(
        TABLE.c.id.desc(), TABLE.c.created_at.asc(), TABLE.c.name.desc()
    )
    prepared, parameters, cursor = prepare_pagination(
        query,
        10,
        cursor=Cursor(
            {
                "id": 42,
                "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
                "name": "Alice",
            }
        ),
    )

    assert prepared.compile().string.replace("\n", "").replace("  ", " ") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE users.id < :id_1 OR users.id = :id_2 AND users.created_at > :created_at_1 OR users.id = :id_3 AND users.created_at = :created_at_2 AND users.name < :name_1 "
        "ORDER BY users.id DESC, users.created_at ASC, users.name DESC "
        "LIMIT :param_1"
    )
    assert prepared.compile().params == {
        "param_1": 11,
        "id_1": 42,
        "id_2": 42,
        "id_3": 42,
        "created_at_1": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "created_at_2": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "name_1": "Alice",
    }
    assert parameters == ["id", "created_at", "name"]
    assert cursor is not None
    assert cursor.parameters == {
        "id": 42,
        "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "name": "Alice",
    }


def test_prepare_pagination_with_multiple_columns_and_different_directions_and_reversed_cursor() -> (
    None
):
    query = TABLE.select().order_by(
        TABLE.c.id.desc(), TABLE.c.created_at.asc(), TABLE.c.name.desc()
    )
    prepared, parameters, cursor = prepare_pagination(
        query,
        10,
        cursor=Cursor(
            {
                "id": 42,
                "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
                "name": "Alice",
            },
            reversed=True,
        ),
    )

    assert prepared.compile().string.replace("\n", "").replace("  ", " ") == (
        "SELECT users.id, users.name, users.created_at "
        "FROM users "
        "WHERE users.id > :id_1 OR users.id = :id_2 AND users.created_at < :created_at_1 OR users.id = :id_3 AND users.created_at = :created_at_2 AND users.name > :name_1 "
        "ORDER BY users.id ASC, users.created_at DESC, users.name ASC "
        "LIMIT :param_1"
    )
    assert prepared.compile().params == {
        "param_1": 11,
        "id_1": 42,
        "id_2": 42,
        "id_3": 42,
        "created_at_1": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "created_at_2": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "name_1": "Alice",
    }
    assert parameters == ["id", "created_at", "name"]
    assert cursor is not None
    assert cursor.parameters == {
        "id": 42,
        "created_at": datetime.fromisoformat("2023-01-01T00:00:00Z"),
        "name": "Alice",
    }
