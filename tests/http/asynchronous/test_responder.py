from pathlib import Path

import pytest

from expanse.core.application import Application
from expanse.http.redirect import Redirect
from expanse.http.request import Request
from expanse.http.responder import AsyncResponder
from expanse.http.response import Response
from expanse.routing.router import Router
from expanse.routing.url_generator import URLGenerator
from expanse.view.view_factory import AsyncViewFactory
from expanse.view.view_finder import ViewFinder
from expanse.view.view_manager import ViewManager


@pytest.fixture()
def redirect(router: Router) -> Redirect:
    request = Request.create("http://example.com")

    return Redirect(router, request, URLGenerator(router, request))


@pytest.fixture
def responder(redirect: Redirect, app: Application) -> AsyncResponder:
    return AsyncResponder(
        AsyncViewFactory(
            ViewManager(
                app,
                ViewFinder([Path(__file__).parent.parent.joinpath("fixtures/views")]),
            )
        ),
        redirect,
    )


def test_redirect(responder: AsyncResponder, redirect: Redirect) -> None:
    assert responder.redirect() == redirect


def test_text(responder: AsyncResponder) -> None:
    response = responder.text("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_html(responder: AsyncResponder) -> None:
    response = responder.html("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_json(responder: AsyncResponder) -> None:
    response = responder.json({"foo": "bar"}, headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"


def test_file(responder: AsyncResponder) -> None:
    response = responder.file(
        Path(__file__).parent.parent.joinpath("fixtures/files/text.txt"),
        headers={"X-Header": "foo"},
    )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/plain"
    assert response.charset is None
    assert response.headers["X-Header"] == "foo"


async def test_view(responder: AsyncResponder) -> None:
    response = await responder.view("view", headers={"X-Header": "foo"})

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.content_type == "text/html"
    assert response.charset == "utf-8"
    assert response.headers["X-Header"] == "foo"
