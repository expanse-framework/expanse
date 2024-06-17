from pathlib import Path

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.routing.redirect import Redirect
from expanse.asynchronous.routing.responder import Responder
from expanse.asynchronous.routing.router import Router
from expanse.asynchronous.view.view_factory import ViewFactory
from expanse.asynchronous.view.view_finder import ViewFinder


def test_redirect(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(ViewFactory(ViewFinder([])), redirect)

    assert responder.redirect() == redirect


async def test_text(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = await responder.text("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


async def test_html(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = await responder.html("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


async def test_json(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = await responder.json({"foo": "bar"}, headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


async def test_file(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([])),
        redirect,
    )

    response = await responder.file(
        Path(__file__).parent.joinpath("fixtures/files/text.txt"),
        headers={"X-Header": "foo"},
    )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset is None
    assert response.headers["X-Header"] == "foo"


async def test_view(router: Router) -> None:
    redirect = Redirect(router, Request.create("http://example.com"))

    responder = Responder(
        ViewFactory(ViewFinder([Path(__file__).parent.joinpath("fixtures/views")])),
        redirect,
    )

    response = await responder.view("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"
