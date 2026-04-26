from pathlib import Path
from typing import Annotated

from expanse.contracts.routing.router import Router
from expanse.contracts.storage.asynchronous.storage import Storage
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

    async def handler(storage: Storage) -> Response:
        await storage.put("test.txt", b"Hello, world!")

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

    async def handler(storage: Annotated[Storage, "named_storage"]) -> Response:
        await storage.put("test.txt", b"Hello, world!")

        return Response()

    router.get("/test", handler)

    client.get("/test")

    assert not tmp_path.joinpath("test.txt").exists()
    assert tmp_path.joinpath("named/test.txt").exists()


def test_as_download_returns_attachment_response(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "default",
        "storages": {
            "default": {"driver": "local", "root": tmp_path},
        },
    }

    content = b"col1,col2\n1,2\n"
    (tmp_path / "report.csv").write_bytes(content)

    async def handler(storage: Storage) -> Response:
        return await storage.as_download("report.csv")

    router.get("/download", handler)

    response = client.get("/download")

    assert response.status_code == 200
    assert response.content == content
    assert (
        response.headers["content-disposition"] == 'attachment; filename="report.csv"'
    )
    assert response.headers["content-length"] == str(len(content))
