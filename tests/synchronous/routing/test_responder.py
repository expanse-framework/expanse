from pathlib import Path

from expanse.http.request import Request
from expanse.http.response import Response
from expanse.routing.redirect import Redirect
from expanse.routing.responder import Responder
from expanse.routing.router import Router
from expanse.view.view_factory import ViewFactory
from expanse.view.view_finder import ViewFinder


def test_redirect(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(ViewFactory(ViewFinder([])), redirect)

    assert responder.redirect() == redirect


def test_text(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = responder.text("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_html(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = responder.html("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_json(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = responder.json({"foo": "bar"}, headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_file(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = responder.file(
        Path(__file__).parent.joinpath("fixtures/files/text.txt"),
        headers={"X-Header": "foo"},
    )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset is None
    assert response.headers["X-Header"] == "foo"


def test_view(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([Path(__file__).parent.joinpath("fixtures/views")])),
        redirect,
    )

    response = responder.view("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"
