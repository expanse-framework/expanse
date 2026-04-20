from pathlib import Path
from typing import Annotated

from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.http.helpers import json
from expanse.http.response import Response
from expanse.http.upload_file import UploadFile
from expanse.testing.client import TestClient


async def single_file_handler(file: UploadFile) -> Response:
    path = await file.save("files")

    return json({"path": path})


async def file_by_name_handler(file: Annotated[UploadFile, "file_2"]) -> Response:
    path = await file.save("files")

    return json({"path": path})


async def save_with_name_handler(file: UploadFile) -> Response:
    path = await file.save("files", name="custom_name.txt")

    return json({"path": path})


async def save_with_storage_handler(file: UploadFile) -> Response:
    path = await file.save("files", storage="local-2", name="custom_name.txt")

    return json({"path": path})


def sync_single_file_handler(file: UploadFile) -> Response:
    path = file.save_sync("files")

    return json({"path": path})


def test_upload_file_can_be_retrieved(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "local",
        "storages": {
            "local": {
                "driver": "local",
                "root": tmp_path,
            },
        },
    }

    router.post("/upload", single_file_handler)

    file_content = b"Hello, world!"
    response = client.post(
        "/upload",
        files={"file": ("hello.txt", file_content, "text/plain")},
    )

    assert response.status_code == 200
    file_path = response.json()["path"]
    assert tmp_path.joinpath(file_path).read_bytes() == file_content


def test_upload_file_can_be_retrieved_by_name(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "local",
        "storages": {
            "local": {
                "driver": "local",
                "root": tmp_path,
            },
        },
    }

    router.post("/upload", file_by_name_handler)

    response = client.post(
        "/upload",
        files={
            "file": ("hello.txt", b"Content of file 1", "text/plain"),
            "file_2": ("hello2.txt", b"Content of file 2", "text/plain"),
        },
    )

    assert response.status_code == 200
    file_path = response.json()["path"]
    assert tmp_path.joinpath(file_path).read_bytes() == b"Content of file 2"


def test_upload_file_can_be_saved_with_custom_name(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "local",
        "storages": {
            "local": {
                "driver": "local",
                "root": tmp_path,
            },
        },
    }

    router.post("/upload", save_with_name_handler)

    response = client.post(
        "/upload",
        files={"file": ("hello.txt", b"Hello, world!", "text/plain")},
    )

    assert response.status_code == 200
    file_path = response.json()["path"]
    assert tmp_path.joinpath(file_path).read_bytes() == b"Hello, world!"
    assert file_path.endswith("custom_name.txt")


def test_upload_file_can_be_saved_with_custom_storage(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "local",
        "storages": {
            "local": {
                "driver": "local",
                "root": tmp_path,
            },
            "local-2": {
                "driver": "local",
                "root": tmp_path.joinpath("storage2"),
            },
        },
    }

    router.post("/upload", save_with_storage_handler)

    response = client.post(
        "/upload",
        files={"file": ("hello.txt", b"Hello, world!", "text/plain")},
    )

    assert response.status_code == 200
    file_path = response.json()["path"]
    assert (
        tmp_path.joinpath("storage2").joinpath(file_path).read_bytes()
        == b"Hello, world!"
    )


def test_upload_file_can_be_saved_synchronously(
    app: Application, router: Router, client: TestClient, tmp_path: Path
) -> None:
    app.config["storage"] = {
        "storage": "local",
        "storages": {
            "local": {
                "driver": "local",
                "root": tmp_path,
            },
        },
    }

    router.post("/upload", sync_single_file_handler)

    file_content = b"Hello, world!"
    response = client.post(
        "/upload",
        files={"file": ("hello.txt", file_content, "text/plain")},
    )

    assert response.status_code == 200
    file_path = response.json()["path"]
    assert tmp_path.joinpath(file_path).read_bytes() == file_content
