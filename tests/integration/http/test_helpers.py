from pathlib import Path

from expanse.contracts.routing.registrar import Registrar
from expanse.http.helpers import abort
from expanse.http.helpers import download
from expanse.http.helpers import file_
from expanse.http.helpers import html
from expanse.http.helpers import json
from expanse.http.helpers import text
from expanse.testing.client import TestClient


def test_abort(router: Registrar, client: TestClient) -> None:
    router.get("/abort", lambda: abort(500, "This is an error message"))

    response = client.get("/abort", headers={"Accept": "application/json"})
    assert response.status_code == 500
    data = response.json()
    assert data["exception"] == "HTTPException"
    assert data["message"] == "This is an error message"
    assert response.headers["Content-Type"] == "application/json"


def test_text(router: Registrar, client: TestClient) -> None:
    router.get("/", lambda: text("This is a message"))

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "This is a message"
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"


def test_html(router: Registrar, client: TestClient) -> None:
    router.get("/", lambda: html("<p>This is a message</p>"))

    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "<p>This is a message</p>"
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_json(router: Registrar, client: TestClient) -> None:
    router.get("/", lambda: json({"foo": "bar"}))

    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"foo": "bar"}
    assert response.headers["Content-Type"] == "application/json"


def test_file(router: Registrar, client: TestClient, tmp_path: Path) -> None:
    test_file = tmp_path.joinpath("test.txt")
    test_file.write_text("This is a test file.")
    router.get("/file", lambda: file_(test_file))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert response.headers["Content-Disposition"] == 'inline; filename="test.txt"'
    assert response.text == "This is a test file."


def test_download(router: Registrar, client: TestClient, tmp_path: Path) -> None:
    test_file = tmp_path.joinpath("test.txt")
    test_file.write_text("This is a test file.")
    router.get("/file", lambda: download(test_file))

    response = client.get("/file")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain"
    assert response.headers["Content-Disposition"] == 'attachment; filename="test.txt"'
    assert response.text == "This is a test file."
