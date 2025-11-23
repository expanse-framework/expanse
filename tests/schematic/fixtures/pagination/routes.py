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
from expanse.pagination.cursor.adapters.envelope import Envelope as CursorEnvelope
from expanse.pagination.cursor.adapters.headers import Headers as CursorHeaders
from expanse.pagination.cursor.cursor_paginator import CursorPaginator
from expanse.pagination.offset.adapters.envelope import Envelope
from expanse.pagination.offset.adapters.headers import Headers
from expanse.pagination.offset.paginator import Paginator
from expanse.routing.helpers import get


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


@get("/paginated/envelope/default")
def paginated_envelope_default(
    session: Session,
) -> Paginator[Annotated[User, UserResponse]]:
    """
    Default paginated envelope example.
    """
    stmt = select(User)

    return session.paginate(stmt)


@get("/paginated/envelope/unannotated-model")
def paginated_envelope_default_unannotated_model(
    session: Session,
) -> Paginator[User]:
    """
    Default paginated envelope example with unannotated models.
    """
    stmt = select(User)

    return session.paginate(stmt)


@get("/paginated/envelope/no-links")
def paginated_envelope_no_links(
    session: Session,
) -> Annotated[Paginator[Annotated[User, UserResponse]], Envelope(with_links=False)]:
    """
    Paginated example without links in the envelope.
    """
    stmt = select(User)

    return session.paginate(stmt)


@get("/paginated/headers/default")
def paginated_headers(
    session: Session,
) -> Annotated[Paginator[Annotated[User, UserResponse]], Headers()]:
    """
    Paginated example with links in headers.
    """
    stmt = select(User)

    return session.paginate(stmt)


@get("/cursor-paginated/envelope/default")
def cursor_paginated_envelope_default(
    session: Session,
) -> CursorPaginator[Annotated[User, UserResponse]]:
    """
    Default cursor paginated envelope example.
    """
    stmt = select(User)

    return session.cursor_paginate(stmt)


@get("/cursor-paginated/envelope/unannotated-model")
def cursor_paginated_envelope_default_unannotated_model(
    session: Session,
) -> CursorPaginator[User]:
    """
    Default cursor paginated envelope example with unannotated models.
    """
    stmt = select(User)

    return session.cursor_paginate(stmt)


@get("/cursor-paginated/envelope/no-links")
def cursor_paginated_envelope_no_links(
    session: Session,
) -> Annotated[
    CursorPaginator[Annotated[User, UserResponse]], CursorEnvelope(with_links=False)
]:
    """
    Cursor paginated example without links in the envelope.
    """
    stmt = select(User)

    return session.cursor_paginate(stmt)


@get("/paginated/headers/default")
def cursor_paginated_headers(
    session: Session,
) -> Annotated[CursorPaginator[Annotated[User, UserResponse]], CursorHeaders()]:
    """
    Cursor paginated example with links in headers.
    """
    stmt = select(User)

    return session.cursor_paginate(stmt)


def routes(router: Registrar) -> None:
    router.handler(paginated_envelope_default)
    router.handler(paginated_envelope_default_unannotated_model)
    router.handler(paginated_envelope_no_links)
    router.handler(paginated_headers)
    router.handler(cursor_paginated_envelope_default)
    router.handler(cursor_paginated_envelope_default_unannotated_model)
    router.handler(cursor_paginated_envelope_no_links)
    router.handler(cursor_paginated_headers)
