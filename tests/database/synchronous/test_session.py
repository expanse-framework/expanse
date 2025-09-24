from datetime import UTC
from datetime import datetime

import pytest

from sqlalchemy import DateTime
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from expanse.core.application import Application
from expanse.database.orm import column
from expanse.database.orm.model import Model
from expanse.database.synchronous.database_manager import DatabaseManager


class User(Model):
    __tablename__ = "users"

    id: Mapped[int] = column(primary_key=True)
    first_name: Mapped[str] = column(nullable=False)
    last_name: Mapped[str] = column(nullable=False)
    email: Mapped[str] = column(nullable=False)
    created_at: Mapped[datetime] = column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )


@pytest.fixture
def db(app: Application) -> DatabaseManager:
    app.config["database"] = {
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        },
    }
    db = DatabaseManager(app)

    with db.session() as session:
        session.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                 id INTEGER NOT NULL,
                 first_name VARCHAR NOT NULL,
                 last_name VARCHAR NOT NULL,
                 email VARCHAR NOT NULL,
                 created_at DATETIME NOT NULL,
                 PRIMARY KEY (id)
            );"""
        )
        for i in range(1, 51):
            session.execute(
                "INSERT INTO users (first_name, last_name, email, created_at) VALUES (:first_name, :last_name, :email, :created_at)",
                {
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                    "email": f"foo{i}@bar.com",
                    "created_at": datetime.now(UTC),
                },
            )
        session.commit()

    return db


def test_paginate_retrieves_the_correct_number_of_items(db: DatabaseManager) -> None:
    with db.session() as session:
        paginator = session.paginate(select(User).order_by(User.id))
        assert len(paginator.items) == 20
        assert paginator.has_more

        paginator = session.paginate(select(User).order_by(User.id), per_page=50)
        assert len(paginator.items) == 50
        assert not paginator.has_more


def test_paginate_accepts_a_cursor_to_start_on_specific_page(
    db: DatabaseManager,
) -> None:
    with db.session() as session:
        paginator = session.paginate(select(User).order_by(User.id))
        cursor = paginator.next_cursor

        paginator = session.paginate(select(User).order_by(User.id), cursor=cursor)
        assert len(paginator.items) == 20
        assert paginator.has_more
        assert paginator.items[0].id == 21


def test_paginate_can_paginate_mix_of_scalars_and_models(
    db: DatabaseManager,
) -> None:
    with db.session() as session:
        paginator = session.paginate(select(User, User.id).order_by(User.id))

        assert len(paginator.items) == 20
        assert paginator.has_more
        assert paginator.items[0].id == 1
        assert paginator.items[0][0].id == 1


def test_paginate_can_paginate_with_only_scalars(
    db: DatabaseManager,
) -> None:
    with db.session() as session:
        paginator = session.paginate(select(User.id, User.email).order_by(User.id))

        assert len(paginator.items) == 20
        assert paginator.has_more
        assert paginator.items[0][0] == 1
        assert paginator.items[0][1] == "foo1@bar.com"
        assert paginator.items[0].id == 1
        assert paginator.items[0].email == 1
