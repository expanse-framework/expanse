from pathlib import Path

import pytest

from expanse.common.core.http.exceptions import HTTPException
from expanse.core.application import Application
from expanse.core.helpers import _use_container
from expanse.http.request import Request
from expanse.static.static import Static


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_get_returns_file_content_if_file_exists(app: Application) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    with app.container.create_scoped_container() as container:
        container.instance(Request, Request.create("http://example.com"))

        with _use_container(container):
            response = static.get("foo.txt")

    assert response.status_code == 200


def test_get_returns_404_not_found_if_file_does_not_exist(app: Application) -> None:
    static = Static([FIXTURES_DIR], prefix="/static")

    with app.container.create_scoped_container() as container:
        container.instance(Request, Request.create("http://example.com"))

        with _use_container(container):
            with pytest.raises(HTTPException) as e:
                static.get("bar.txt")

            assert e.value.status_code == 404
