from pathlib import Path

from expanse.contracts.routing.router import Router
from expanse.testing.client import TestClient


def test_routes_are_properly_loaded_from_file(
    router: Router, client: TestClient
) -> None:
    router.load_file(Path("tests/integration/routing/fixtures/routes/web.py"))
    response = client.get("/")

    assert response.text == "Hello, world!"
