from pytest_mock import MockerFixture

from expanse.core.application import Application
from expanse.session.asynchronous.stores.database import AsyncDatabaseStore
from expanse.session.session_manager import SessionManager
from expanse.session.synchronous.stores.database import DatabaseStore


async def test_stores_can_be_configured_through_environment_variables(
    unbootstrapped_app: Application, mocker: MockerFixture
):
    mocker.patch.dict(
        "os.environ",
        {
            "SESSION_STORE": "database",
            "SESSION_STORES__DATABASE__TABLE": "not_sessions",
            "SESSION_STORES__DATABASE__CONNECTION": "my_connection",
        },
    )

    await unbootstrapped_app.bootstrap()
    await unbootstrapped_app.boot()

    manager = SessionManager(unbootstrapped_app)

    stores = await manager.stores()

    assert isinstance(stores[0], DatabaseStore)
    assert isinstance(stores[1], AsyncDatabaseStore)
    assert stores[0]._table.name == "not_sessions"
    assert stores[0]._database_name == "my_connection"
