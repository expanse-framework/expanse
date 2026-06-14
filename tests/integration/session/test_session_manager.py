import pytest

from expanse.core.application import Application
from expanse.session.asynchronous.stores.cache import AsyncCacheStore
from expanse.session.config import RedisStoreConfig
from expanse.session.session_manager import SessionManager
from expanse.session.synchronous.stores.cache import CacheStore


@pytest.fixture()
def session_manager(app: Application) -> SessionManager:
    app.config["session.store"] = "redis"
    app.config["session.stores"] = {
        "redis": RedisStoreConfig(connection="default"),
    }

    return SessionManager(app)


@pytest.mark.redis
async def test_session_manager_can_create_a_redis_stores(
    session_manager: SessionManager,
) -> None:
    stores = await session_manager.stores()

    assert isinstance(stores[0], CacheStore)
    assert isinstance(stores[1], AsyncCacheStore)
