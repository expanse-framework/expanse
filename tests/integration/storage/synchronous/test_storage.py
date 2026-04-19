from pathlib import Path
from typing import Annotated

from expanse.contracts.routing.router import Router
from expanse.contracts.storage.synchronous.storage import Storage
from expanse.core.application import Application
from expanse.http.responses.response import Response
from expanse.testing.client import TestClient


def test_storage_can_be_injected(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "default",
        "storages": {
            "default": {"driver": "local", "root": tmp_path},
        },
    }

    def handler(storage: Storage) -> Response:
        storage.put("test.txt", b"Hello, world!")

        return Response()

    router.get("/test", handler)

    client.get("/test")

    assert tmp_path.joinpath("test.txt").exists()


def test_storage_can_be_injected_by_name(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "default",
        "storages": {
            "default": {"driver": "local", "root": tmp_path},
            "named_storage": {"driver": "local", "root": tmp_path / "named"},
        },
    }

    def handler(storage: Annotated[Storage, "named_storage"]) -> Response:
        storage.put("test.txt", b"Hello, world!")

        return Response()

    router.get("/test", handler)

    client.get("/test")

    assert not tmp_path.joinpath("test.txt").exists()
    assert tmp_path.joinpath("named/test.txt").exists()
