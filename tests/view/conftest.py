from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from expanse.http.request import Request


if TYPE_CHECKING:
    from expanse.core.application import Application


@pytest.fixture(autouse=True)
async def setup_app(app: Application) -> None:
    app.config["view"] = {
        "paths": [Path(__file__).parent.joinpath("fixtures/resources/views")]
    }

    app.container.instance(Request, Request.create("http://example.com"))
