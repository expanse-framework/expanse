from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from expanse.view.view_service_provider import ViewServiceProvider


if TYPE_CHECKING:
    from expanse.core.application import Application


@pytest.fixture(autouse=True)
def setup_app_config(app: Application) -> None:
    config: dict[str, dict[str, Any]] = app.container.make("config")

    config["view"] = {
        "paths": [Path(__file__).parent.joinpath("fixtures/resources/views")]
    }

    app.register(ViewServiceProvider(app.container))
