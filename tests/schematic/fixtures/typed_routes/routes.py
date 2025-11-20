from collections.abc import Sequence
from typing import Annotated
from typing import ClassVar

from pydantic import BaseModel
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from expanse.contracts.routing.registrar import Registrar
from expanse.database.orm import column
from expanse.database.orm.model import Model
from expanse.database.synchronous.session import Session
from expanse.http.helpers import abort
from expanse.http.json import JSON
from expanse.http.query import Query
from expanse.http.responses.response import Response
from expanse.routing.helpers import delete
from expanse.routing.helpers import get
from expanse.routing.helpers import patch
from expanse.routing.helpers import post


class User(Model):
    __tablename__ = "schematic_users"

    id: Mapped[int] = column(primary_key=True)
    name: Mapped[str] = column(init=True)
    email: Mapped[str] = column(init=True)

    metadata: ClassVar[MetaData] = MetaData()


class UserRequest(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class UserFilters(BaseModel):
    name: str | None = None
    email: str | None = None


@get("/users", name="user.list")
def list_users(
    session: Session, filters: Query[UserFilters]
) -> Sequence[Annotated[User, UserResponse]]:
    stmt = select(User)
    if filters.name is not None:
        stmt = stmt.where(User.name == filters.name)
    if filters.email is not None:
        stmt = stmt.where(User.email == filters.email)

    users = session.scalars(stmt).all()

    return users


@post("/users", name="user.create")
def create_user(
    session: Session, data: JSON[UserRequest]
) -> Annotated[User, UserResponse]:
    user = User(name=data.name, email=data.email)
    session.add(user)
    session.commit()

    return user


@patch("/users/{user_id}", name="user.update")
def update_user(
    session: Session, user_id: int, data: JSON[UserRequest]
) -> Annotated[User, UserResponse]:
    user = session.get(User, user_id)
    if user is None:
        abort(404, "User not found")

    user.name = data.name
    user.email = data.email
    session.commit()

    return user


@delete("/users/{user_id}", name="user.delete")
def delete_user(session: Session, user_id: int) -> Response:
    user = session.get(User, user_id)
    if user is None:
        abort(404, "User not found")

    session.delete(user)
    session.commit()

    return Response(status_code=204)


def routes(router: Registrar) -> None:
    router.handler(list_users)
    router.handler(create_user)
    router.handler(update_user)
    router.handler(delete_user)
