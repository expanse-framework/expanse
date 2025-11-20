from typing import Annotated

import pytest

from pydantic import BaseModel
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.database.database_manager import AsyncDatabaseManager
from expanse.database.orm import column
from expanse.database.orm.model import Model
from expanse.database.session import AsyncSession
from expanse.pagination.cursor.adapters.envelope import Envelope
from expanse.pagination.cursor.cursor_paginator import CursorPaginator
from expanse.testing.client import TestClient


@pytest.fixture(autouse=True)
async def create_users(app: Application) -> None:
    db = await app.container.get(AsyncDatabaseManager)
    async with db.session() as session:
        for i in range(51):
            user = User()
            user.first_name = f"First{i}"
            user.last_name = f"Last{i}"
            user.email = f"foo{i}@bar.com"
            session.add(user)

        await session.commit()


class User(Model):
    metadata: MetaData = MetaData()

    __tablename__ = "users"

    id: Mapped[int] = column(primary_key=True)
    first_name: Mapped[str] = column(nullable=False)
    last_name: Mapped[str] = column(nullable=False)
    email: Mapped[str] = column(nullable=False)


class UserSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


async def paginated(
    session: AsyncSession,
) -> CursorPaginator[Annotated[User, UserSchema]]:
    paginator = await session.cursor_paginate(
        select(User).order_by(User.id), per_page=2
    )

    return paginator


async def paginated_no_links(
    session: AsyncSession,
) -> Annotated[
    CursorPaginator[Annotated[User, UserSchema]], Envelope(with_links=False)
]:
    paginator = await session.cursor_paginate(
        select(User).order_by(User.id), per_page=2
    )

    return paginator


async def test_session_cursor_pagination_is_properly_serialized(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    data = response.json()
    assert response.json()["data"] == [
        {
            "id": 1,
            "first_name": "First0",
            "last_name": "Last0",
            "email": "foo0@bar.com",
        },
        {
            "id": 2,
            "first_name": "First1",
            "last_name": "Last1",
            "email": "foo1@bar.com",
        },
    ]
    assert data["next_cursor"] is not None
    assert data["previous_cursor"] is None
    assert (
        data["links"]["next"]
        == f"http://testserver/paginated?cursor={data['next_cursor']}"
    )
    assert data["links"]["prev"] is None


async def test_session_cursor_pagination_uses_given_cursor(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    data = response.json()
    cursor = data["next_cursor"]

    response = client.get(
        "/paginated",
        headers={"Accept": "application/json"},
        params={"cursor": cursor},
    )

    data = response.json()
    assert data["data"] == [
        {
            "id": 3,
            "first_name": "First2",
            "last_name": "Last2",
            "email": "foo2@bar.com",
        },
        {
            "id": 4,
            "first_name": "First3",
            "last_name": "Last3",
            "email": "foo3@bar.com",
        },
    ]
    next_cursor = data["next_cursor"]
    assert next_cursor is not None
    prev_cursor = data["previous_cursor"]
    assert prev_cursor is not None
    assert (
        data["links"]["next"]
        == f"http://testserver/paginated?cursor={data['next_cursor']}"
    )
    assert (
        data["links"]["prev"]
        == f"http://testserver/paginated?cursor={data['previous_cursor']}"
    )

    cursor = data["previous_cursor"]

    response = client.get(
        "/paginated",
        headers={"Accept": "application/json"},
        params={"cursor": cursor},
    )

    data = response.json()
    assert (
        data["data"]
        == response.json()["data"]
        == [
            {
                "id": 1,
                "first_name": "First0",
                "last_name": "Last0",
                "email": "foo0@bar.com",
            },
            {
                "id": 2,
                "first_name": "First1",
                "last_name": "Last1",
                "email": "foo1@bar.com",
            },
        ]
    )


async def test_session_cursor_pagination_with_no_links(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated_no_links)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    data = response.json()
    assert response.json()["data"] == [
        {
            "id": 1,
            "first_name": "First0",
            "last_name": "Last0",
            "email": "foo0@bar.com",
        },
        {
            "id": 2,
            "first_name": "First1",
            "last_name": "Last1",
            "email": "foo1@bar.com",
        },
    ]
    assert data["next_cursor"] is not None
    assert data["previous_cursor"] is None
    assert "links" not in data


async def test_session_cursor_pagination_keeps_query_parameters(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get(
        "/paginated",
        headers={"Accept": "application/json"},
        params={"foo": "bar", "baz": "qux"},
    )

    data = response.json()
    assert response.json()["data"] == [
        {
            "id": 1,
            "first_name": "First0",
            "last_name": "Last0",
            "email": "foo0@bar.com",
        },
        {
            "id": 2,
            "first_name": "First1",
            "last_name": "Last1",
            "email": "foo1@bar.com",
        },
    ]
    assert data["links"]["next"] == (
        f"http://testserver/paginated?foo=bar&baz=qux&cursor={data['next_cursor']}"
    )
