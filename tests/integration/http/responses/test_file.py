from pathlib import Path

import pendulum

from expanse.contracts.routing.registrar import Registrar
from expanse.http.responses.file import FileResponse
from expanse.testing.client import TestClient


def test_file_response(router: Registrar, client: TestClient, tmp_path: Path) -> None:
    tmp_path.joinpath("test.txt").write_text("This is a test file.")
    router.get("/file", lambda: FileResponse(tmp_path.joinpath("test.txt")))

    modified_at = pendulum.from_timestamp(tmp_path.joinpath("test.txt").stat().st_mtime)
    response = client.get("/file")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert response.headers["Content-Disposition"] == 'inline; filename="test.txt"'
    assert response.headers["Content-Length"] == "20"
    assert "Content-Encoding" not in response.headers
    assert response.headers["Last-Modified"] == modified_at.format(
        "ddd, DD MMM YYYY HH:mm:ss [GMT]"
    )
    assert response.text == "This is a test file."


def test_file_response_with_unknown_type(
    router: Registrar, client: TestClient, tmp_path: Path
) -> None:
    tmp_path.joinpath("test").write_text("This is a test file.")
    router.get("/file", lambda: FileResponse(tmp_path.joinpath("test")))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert response.headers["Content-Disposition"] == 'inline; filename="test"'
    assert response.text == "This is a test file."


def test_file_response_with_big_file(
    router: Registrar, client: TestClient, tmp_path: Path
) -> None:
    with tmp_path.joinpath("test").open("wb") as f:
        f.write(b"F" * 1024 * 1024 * 3)

    router.get("/file", lambda: FileResponse(tmp_path.joinpath("test")))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert response.headers["Content-Disposition"] == 'inline; filename="test"'
    assert response.content == b"F" * 1024 * 1024 * 3


def test_file_response_as_attachment(
    router: Registrar, client: TestClient, tmp_path: Path
) -> None:
    tmp_path.joinpath("test.txt").write_text("This is a test file.")
    router.get(
        "/file",
        lambda: FileResponse(
            tmp_path.joinpath("test.txt"), content_disposition="attachment"
        ),
    )

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert response.headers["Content-Disposition"] == 'attachment; filename="test.txt"'
    assert response.text == "This is a test file."


def test_file_response_with_encoding(
    router: Registrar, client: TestClient, tmp_path: Path
) -> None:
    tmp_path.joinpath("test.gz").touch()
    router.get("/file", lambda: FileResponse(tmp_path.joinpath("test.gz")))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert response.headers["Content-Disposition"] == 'inline; filename="test.gz"'
    assert response.headers["Content-Length"] == "0"
    assert response.headers["Content-Encoding"] == "gzip"
    assert response.headers["Last-Modified"] is not None


def test_file_response_with_special_characters(
    router: Registrar, client: TestClient, tmp_path: Path
) -> None:
    tmp_path.joinpath("test test é.txt").write_text("This is a test file.")
    router.get("/file", lambda: FileResponse(tmp_path.joinpath("test test é.txt")))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert (
        response.headers["Content-Disposition"]
        == "inline; filename*=UTF-8''test%20test%20%C3%A9.txt"
    )
    assert response.headers["Content-Length"] == "20"
    assert "Content-Encoding" not in response.headers
    assert response.headers["Last-Modified"] is not None
    assert response.text == "This is a test file."
