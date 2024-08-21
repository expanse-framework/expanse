import pytest

from expanse.asynchronous.core.application import Application
from expanse.asynchronous.core.bootstrap.load_configuration import LoadConfiguration
from expanse.common.configuration.config import Config


@pytest.fixture()
def app() -> Application:
    return Application()


async def test_loading_configuration_provides_default_values(app: Application) -> None:
    await LoadConfiguration.bootstrap(app)

    config = await app.container.make(Config)

    assert config["app.name"] == "Expanse"
    assert len(config["app.providers"]) > 0
