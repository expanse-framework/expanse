import pytest

from expanse.common.configuration.config import Config
from expanse.foundation.application import Application
from expanse.foundation.bootstrap.load_configuration import LoadConfiguration


@pytest.fixture()
def app() -> Application:
    return Application()


def test_loading_configuration_provides_default_values(app: Application) -> None:
    LoadConfiguration.bootstrap(app)

    config = app.make(Config)

    assert config["app.name"] == "Expanse"
    assert len(config["app.providers"]) > 0
