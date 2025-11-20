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
from expanse.pagination.offset.adapters.envelope import Envelope
from expanse.pagination.offset.adapters.headers import Headers
from expanse.pagination.offset.paginator import Paginator
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
) -> Paginator[Annotated[User, UserSchema]]:
    paginator = await session.paginate(select(User).order_by(User.id), per_page=2)

    return paginator


async def paginated_no_links(
    session: AsyncSession,
) -> Annotated[Paginator[Annotated[User, UserSchema]], Envelope(with_links=False)]:
    paginator = await session.paginate(select(User).order_by(User.id), per_page=2)

    return paginator


async def paginated_headers(
    session: AsyncSession,
) -> Annotated[Paginator[Annotated[User, UserSchema]], Headers()]:
    paginator = await session.paginate(select(User).order_by(User.id), per_page=2)

    return paginator


async def test_session_pagination_is_properly_serialized(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    assert response.json() == {
        "data": [
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
        ],
        "next_page": 2,
        "previous_page": None,
        "current_page": 1,
        "first_page": 1,
        "last_page": 26,
        "total": 51,
        "links": {
            "next": "http://testserver/paginated?page=2",
            "prev": None,
            "first": "http://testserver/paginated?page=1",
            "last": "http://testserver/paginated?page=26",
            "self": "http://testserver/paginated?page=1",
        },
    }


async def test_session_pagination_uses_given_page(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get(
        "/paginated", headers={"Accept": "application/json"}, params={"page": 2}
    )

    assert response.json() == {
        "data": [
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
        ],
        "next_page": 3,
        "previous_page": 1,
        "current_page": 2,
        "first_page": 1,
        "last_page": 26,
        "total": 51,
        "links": {
            "next": "http://testserver/paginated?page=3",
            "prev": "http://testserver/paginated?page=1",
            "first": "http://testserver/paginated?page=1",
            "last": "http://testserver/paginated?page=26",
            "self": "http://testserver/paginated?page=2",
        },
    }


async def test_session_pagination_last_page(router: Router, client: TestClient) -> None:
    router.get("/paginated", paginated)

    response = client.get(
        "/paginated", headers={"Accept": "application/json"}, params={"page": 26}
    )

    assert response.json() == {
        "data": [
            {
                "id": 51,
                "first_name": "First50",
                "last_name": "Last50",
                "email": "foo50@bar.com",
            },
        ],
        "next_page": None,
        "previous_page": 25,
        "current_page": 26,
        "first_page": 1,
        "last_page": 26,
        "total": 51,
        "links": {
            "next": None,
            "prev": "http://testserver/paginated?page=25",
            "first": "http://testserver/paginated?page=1",
            "last": "http://testserver/paginated?page=26",
            "self": "http://testserver/paginated?page=26",
        },
    }


async def test_session_pagination_with_no_links(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated_no_links)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    assert response.json() == {
        "data": [
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
        ],
        "next_page": 2,
        "previous_page": None,
        "current_page": 1,
        "first_page": 1,
        "last_page": 26,
        "total": 51,
    }


async def test_session_pagination_keeps_query_parameters(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated)

    response = client.get(
        "/paginated",
        headers={"Accept": "application/json"},
        params={"foo": "bar", "baz": "qux"},
    )

    assert response.json() == {
        "data": [
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
        ],
        "next_page": 2,
        "previous_page": None,
        "current_page": 1,
        "first_page": 1,
        "last_page": 26,
        "total": 51,
        "links": {
            "next": "http://testserver/paginated?foo=bar&baz=qux&page=2",
            "prev": None,
            "first": "http://testserver/paginated?foo=bar&baz=qux&page=1",
            "last": "http://testserver/paginated?foo=bar&baz=qux&page=26",
            "self": "http://testserver/paginated?foo=bar&baz=qux&page=1",
        },
    }


def test_session_pagination_headers(router: Router, client: TestClient) -> None:
    router.get("/paginated", paginated_headers)

    response = client.get("/paginated", headers={"Accept": "application/json"})

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "51"
    links = response.headers["Link"]
    assert links == ", ".join(
        [
            '<http://testserver/paginated?page=2>; rel="next"',
            '<http://testserver/paginated?page=1>; rel="first"',
            '<http://testserver/paginated?page=26>; rel="last"',
            '<http://testserver/paginated?page=1>; rel="self"',
        ]
    )

    assert response.json() == [
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


def test_session_pagination_headers_with_page(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated_headers)

    response = client.get(
        "/paginated", headers={"Accept": "application/json"}, params={"page": 2}
    )

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "51"
    links = response.headers["Link"]
    assert links == ", ".join(
        [
            '<http://testserver/paginated?page=3>; rel="next"',
            '<http://testserver/paginated?page=1>; rel="prev"',
            '<http://testserver/paginated?page=1>; rel="first"',
            '<http://testserver/paginated?page=26>; rel="last"',
            '<http://testserver/paginated?page=2>; rel="self"',
        ]
    )

    assert response.json() == [
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


def test_session_pagination_headers_for_last_page(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated_headers)

    response = client.get(
        "/paginated", headers={"Accept": "application/json"}, params={"page": 26}
    )

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "51"
    links = response.headers["Link"]
    assert links == ", ".join(
        [
            '<http://testserver/paginated?page=25>; rel="prev"',
            '<http://testserver/paginated?page=1>; rel="first"',
            '<http://testserver/paginated?page=26>; rel="last"',
            '<http://testserver/paginated?page=26>; rel="self"',
        ]
    )

    assert response.json() == [
        {
            "id": 51,
            "first_name": "First50",
            "last_name": "Last50",
            "email": "foo50@bar.com",
        },
    ]


def test_session_pagination_headers_keeps_query_parameters(
    router: Router, client: TestClient
) -> None:
    router.get("/paginated", paginated_headers)

    response = client.get(
        "/paginated",
        headers={"Accept": "application/json"},
        params={
            "foo": "bar bar",
            "baz": "qux",
            "page": 2,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "51"
    links = response.headers["Link"]
    assert links == ", ".join(
        [
            '<http://testserver/paginated?foo=bar+bar&baz=qux&page=3>; rel="next"',
            '<http://testserver/paginated?foo=bar+bar&baz=qux&page=1>; rel="prev"',
            '<http://testserver/paginated?foo=bar+bar&baz=qux&page=1>; rel="first"',
            '<http://testserver/paginated?foo=bar+bar&baz=qux&page=26>; rel="last"',
            '<http://testserver/paginated?foo=bar+bar&baz=qux&page=2>; rel="self"',
        ]
    )

    assert response.json() == [
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
