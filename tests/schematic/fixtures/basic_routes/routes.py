from typing import Any

from expanse.contracts.routing.registrar import Registrar
from expanse.http.responses.response import Response
from expanse.routing.helpers import delete
from expanse.routing.helpers import get
from expanse.routing.helpers import patch
from expanse.routing.helpers import post


@get("/users", name="user.list")
async def list_users() -> list[dict[str, Any]]:
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


@post("/users", name="user.create")
async def create_user(data: dict[str, Any]) -> dict[str, Any]:
    return {"id": 3, "name": data.get("name", "Unknown")}


@patch("/users/{user_id}", name="user.update")
async def update_user(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    return {"id": user_id, "name": data.get("name", "Updated Name")}


@delete("/users/{user_id}", name="user.delete")
async def delete_user(user_id: int) -> Response:
    return Response(status_code=204)


def routes(router: Registrar) -> None:
    router.handler(list_users)
    router.handler(create_user)
    router.handler(update_user)
    router.handler(delete_user)
