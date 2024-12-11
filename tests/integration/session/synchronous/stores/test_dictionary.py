import json

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from expanse.session.synchronous.stores.dict import DictStore


def test_store_can_read_from_the_dict() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }

    assert store.read(session_id) == json.dumps({"foo": "bar"})


def test_store_can_write_data() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }

    store.write(session_id, json.dumps({"bar": "baz"}))

    session = store._sessions[session_id]

    assert session["data"] == json.dumps({"bar": "baz"})
    assert session["time"] <= datetime.now(timezone.utc)


def test_store_can_delete_sessions() -> None:
    session_id = "s" * 40

    store = DictStore(120)
    store._sessions[session_id] = {
        "time": datetime.now(timezone.utc),
        "data": json.dumps({"foo": "bar"}),
    }

    store.delete(session_id)

    assert session_id not in store._sessions


def test_expired_sessions_can_be_cleared() -> None:
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

    assert store.clear() == 1
    assert store.clear() == 0

    assert store.read(session_id) != ""
    assert store.read("t" * 40) == ""
