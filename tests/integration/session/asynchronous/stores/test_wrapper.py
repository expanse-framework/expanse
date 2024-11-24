import json

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from expanse.session.asynchronous.stores.wrapper import AsyncWrapperStore
from expanse.session.synchronous.stores.dict import DictStore


pytestmark = pytest.mark.db


async def test_store_can_read_from_the_dict() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }
    async_store = AsyncWrapperStore(store)

    assert await async_store.read(session_id) == json.dumps({"foo": "bar"})


async def test_store_can_write_session_data() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }
    async_store = AsyncWrapperStore(store)

    await async_store.write(session_id, json.dumps({"bar": "baz"}))

    session = store._sessions[session_id]

    assert session["data"] == json.dumps({"bar": "baz"})
    assert session["time"] <= datetime.now(timezone.utc)


async def test_store_can_delete_session_data() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }
    async_store = AsyncWrapperStore(store)

    await async_store.delete(session_id)

    assert session_id not in store._sessions


async def test_expired_sessions_can_be_cleared() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }
    store._sessions["t" * 40] = {
        "time": datetime.now(timezone.utc) - timedelta(minutes=180),
        "data": json.dumps({"foo": "bar"}),
    }
    async_store = AsyncWrapperStore(store)

    assert await async_store.clear() == 1
    assert await async_store.clear() == 0

    assert await async_store.read(session_id) != ""
    assert await async_store.read("t" * 40) == ""
