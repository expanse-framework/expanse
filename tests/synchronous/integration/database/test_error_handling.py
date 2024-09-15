from dataclasses import asdict

from sqlalchemy import select

from expanse.database.session import Session
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.testing.client import TestClient
from tests.synchronous.integration.database.models import User


def show(session: Session, user_email: str) -> Response:
    user = session.scalars(select(User).where(User.email == user_email).limit(1)).one()

    return json(asdict(user))


def test_no_result_found_errors_return_404_errors(router: Router, client: TestClient):
    router.get("/users/{user_email}", show)

    response = client.get("/users/john@doe.com", headers={"Accept": "application/json"})

    assert response.status_code == 200

    response = client.get("/users/jane@doe.com", headers={"Accept": "application/json"})

    assert response.status_code == 404
    assert response.json() == {
        "exception": "HTTPException",
        "message": "No row was found when one was required",
    }
