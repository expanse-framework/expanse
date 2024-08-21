from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from expanse.asynchronous.view.view_service_provider import ViewServiceProvider


if TYPE_CHECKING:
    from expanse.asynchronous.core.application import Application


@pytest.fixture(autouse=True)
async def setup_app_config(app: Application) -> None:
    config: dict[str, dict[str, Any]] = await app.container.make("config")

    config["view"] = {
        "paths": [Path(__file__).parent.joinpath("fixtures/resources/views")]
    }

    await app.register(ViewServiceProvider(app.container))
