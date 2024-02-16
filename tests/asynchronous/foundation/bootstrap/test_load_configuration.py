import pytest

from expanse.asynchronous.foundation.application import Application
from expanse.asynchronous.foundation.bootstrap.load_configuration import (
    LoadConfiguration,
)
from expanse.common.configuration.config import Config


@pytest.fixture()
def app() -> Application:
    return Application()


async def test_loading_configuration_provides_default_values(app: Application) -> None:
    await LoadConfiguration.bootstrap(app)

    config = await app.make(Config)

    assert config["app.name"] == "Expanse"
    assert len(config["app.providers"]) > 0
