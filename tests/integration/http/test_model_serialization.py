from pathlib import Path
from typing import Annotated

import pytest
import sqlalchemy as sa

from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.database.orm.types.encrypted import Encrypted
from expanse.database.session import AsyncSession
from expanse.testing.client import TestClient


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "enc_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column(Encrypted(255))


class UserData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


async def create_user(session: AsyncSession) -> Annotated[User, UserData]:
    user = User(name="John", email="john@example.com")

    session.add(user)
    await session.commit()

    return user


@pytest.fixture(autouse=True)
def _setup(app: Application, tmp_path: Path) -> None:
    app.config["database"] = {
        "default": "sqlite",
        "connections": {
            "sqlite": {"driver": "sqlite", "database": tmp_path.joinpath("db.sqlite")}
        },
    }

    engine = sa.create_engine(f"sqlite:///{tmp_path.joinpath('db.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    engine.dispose()


async def test_model_created_in_endpoint_can_be_serialized(
    router: Router, client: TestClient
) -> None:
    # Committing expires every attribute when expire_on_commit is left on, and the
    # refresh that the serializer then triggers is IO outside of any SQLAlchemy
    # greenlet, which fails with a MissingGreenlet error.
    router.post("/users", create_user)

    response = client.post("/users")

    assert response.status_code == 200, response.text
    assert response.json() == {"id": 1, "name": "John", "email": "john@example.com"}
