from dataclasses import asdict

from sqlalchemy import select

from expanse.asynchronous.database.session import Session
from expanse.asynchronous.http.helpers import json
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.testing.client import TestClient
from tests.asynchronous.integration.database.models import User


async def show(session: Session, user_email: str) -> Response:
    user = (
        await session.scalars(select(User).where(User.email == user_email).limit(1))
    ).one()

    return await json(asdict(user))


async def test_no_result_found_errors_return_404_errors(
    router: Router, client: TestClient
):
    router.get("/users/{user_email}", show)

    response = client.get("/users/john@doe.com", headers={"Accept": "application/json"})

    assert response.status_code == 200

    response = client.get("/users/jane@doe.com", headers={"Accept": "application/json"})

    assert response.status_code == 404
    assert response.json() == {
        "exception": "HTTPException",
        "message": "No row was found when one was required",
    }
