import json
import secrets

import pytest

from expanse.session.asynchronous.stores.store import AsyncStore
from expanse.session.asynchronous.stores.wrapper import AsyncWrapperStore
from expanse.session.session import HTTPSession
from expanse.session.synchronous.stores.dict import DictStore
from expanse.session.synchronous.stores.store import Store


@pytest.fixture()
def store() -> DictStore:
    return DictStore(lifetime=120)


@pytest.fixture()
def async_store(store: DictStore) -> AsyncWrapperStore:
    return AsyncWrapperStore(store)


@pytest.fixture()
def session(store: Store, async_store: AsyncStore) -> HTTPSession:
    return HTTPSession("name", store, async_store, id="s" * 40)


def test_session_is_loaded_from_the_configured_stores(
    session: HTTPSession, store: Store
) -> None:
    session.load()

    assert session.get("key") is None

    store.write(session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}}))

    session.load()

    assert session.get("key") == "value"
    assert session.get("foo.bar") == "baz"
    assert session["key"] == "value"
    assert session["foo.bar"] == "baz"
    assert session.get("bar", "baz") == "baz"
    assert "key" in session
    assert "bar" not in session
    assert "foo.bar" in session
    assert session.has("key")
    assert not session.has("bar")
    assert session.is_loaded()


async def test_session_is_async_loaded_from_the_configured_stores(
    session: HTTPSession, async_store: AsyncStore
) -> None:
    await session.async_load()

    assert session.get("key") is None

    await async_store.write(
        session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}})
    )

    await session.async_load()

    assert session.get("key") == "value"
    assert session["key"] == "value"
    assert session["foo.bar"] == "baz"
    assert session.get("bar", "baz") == "baz"
    assert "key" in session
    assert "bar" not in session
    assert "foo.bar" in session
    assert session.has("key")
    assert not session.has("bar")
    assert session.is_loaded()


def test_session_is_saved_to_the_configured_stores(
    session: HTTPSession, store: Store
) -> None:
    session.load()

    session["key"] = "value"
    session.flash("flash", "message")

    session.save()

    assert store.read(session.get_id()) == json.dumps(
        {
            "_csrf_token": session.get_csrf_token(),
            "key": "value",
            "flash": "message",
            "_flash": {"new": [], "old": ["flash"]},
        }
    )


async def test_session_is_async_saved_to_the_configured_stores(
    session: HTTPSession, async_store: AsyncStore
) -> None:
    await session.async_load()

    session["key"] = "value"
    session.flash("flash", "message")

    await session.async_save()

    assert (await async_store.read(session.get_id())) == json.dumps(
        {
            "_csrf_token": session.get_csrf_token(),
            "key": "value",
            "flash": "message",
            "_flash": {"new": [], "old": ["flash"]},
        }
    )


def test_session_can_can_be_updated_synchronously(
    session: HTTPSession, store: Store
) -> None:
    token = secrets.token_urlsafe(40)

    store.write(
        session.get_id(),
        json.dumps(
            {
                "_csrf_token": token,
                "key": "value",
                "flash": "message",
                "_flash": {"new": [], "old": ["flash"]},
            }
        ),
    )

    session.load()

    session.set("key", "new value")

    session.save()

    assert store.read(session.get_id()) == json.dumps(
        {
            "_csrf_token": token,
            "key": "new value",
            "_flash": {"new": [], "old": []},
        }
    )


async def test_session_can_can_be_updated_asynchronously(
    session: HTTPSession, async_store: AsyncStore
) -> None:
    token = secrets.token_urlsafe(40)

    await async_store.write(
        session.get_id(),
        json.dumps(
            {
                "_csrf_token": token,
                "key": "value",
                "flash": "message",
                "_flash": {"new": [], "old": ["flash"]},
            }
        ),
    )

    await session.async_load()

    session.set("key", "new value")

    await session.async_save()

    assert (await async_store.read(session.get_id())) == json.dumps(
        {
            "_csrf_token": token,
            "key": "new value",
            "_flash": {"new": [], "old": []},
        }
    )


def test_session_can_flash_data(session: HTTPSession) -> None:
    session.flash("key", "value")
    session.flash("number", 42)
    session.flash("is_active", True)

    assert session.has("key")
    assert session["key"] == "value"
    assert session["number"] == 42
    assert session["is_active"]
    assert session.get("_flash.new") == ["key", "number", "is_active"]

    session.ripen_flash_data()

    assert session.has("key")
    assert session["key"] == "value"
    assert session["number"] == 42
    assert session["is_active"]
    assert session.get("_flash.old") == ["key", "number", "is_active"]
    assert session.get("_flash.new") == []

    session.ripen_flash_data()

    assert not session.has("key")
    assert not session.has("number")
    assert not session.has("is_active")
    assert session.get("_flash.old") == []
    assert session.get("_flash.new") == []


def test_session_can_reflash_data(session: HTTPSession) -> None:
    session.flash("key", "value")
    session.flash("number", 42)
    session.flash("is_active", True)

    assert session.has("key")
    assert session["key"] == "value"
    assert session["number"] == 42
    assert session["is_active"]
    assert session.get("_flash.new") == ["key", "number", "is_active"]

    session.ripen_flash_data()

    assert session.has("key")
    assert session["key"] == "value"
    assert session["number"] == 42
    assert session["is_active"]
    assert session.get("_flash.old") == ["key", "number", "is_active"]
    assert session.get("_flash.new") == []

    session.reflash(["key", "number"])

    session.ripen_flash_data()

    assert session.has("key")
    assert session.has("number")
    assert not session.has("is_active")
    assert session.get("_flash.old") == ["key", "number"]
    assert session.get("_flash.new") == []


def test_csrf_tokens_can_be_regenerated(session: HTTPSession) -> None:
    token = session.get_csrf_token()

    session.regenerate_csrf_token()

    assert session.get_csrf_token() != token


def test_session_can_append_values_to_keys(session: HTTPSession) -> None:
    session["key"] = [1, 2, 3]
    session.append("key", 4)

    assert session["key"] == [1, 2, 3, 4]

    session.append("foo", 5)

    assert session["foo"] == [5]


def test_session_can_be_cleared(session: HTTPSession) -> None:
    session["key"] = "value"
    session["foo"] = "bar"

    assert session["foo"] == "bar"
    assert session["key"] == "value"

    session.clear()

    assert not session.has("foo")
    assert not session.has("key")


def test_session_can_generate_new_ids(session: HTTPSession) -> None:
    old_id = session.get_id()

    session.generate_new_id()

    assert session.get_id() != old_id


def test_session_can_generate_new_ids_and_delete_existing_id_synchronously(
    session: HTTPSession, store: Store
) -> None:
    store.write(session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}}))

    session.load()

    old_id = session.get_id()

    session.generate_new_id(delete=True)

    assert store.read(old_id) == ""

    assert session.all() == {
        "_csrf_token": session.get_csrf_token(),
        "key": "value",
        "foo": {"bar": "baz"},
    }


async def test_session_can_generate_new_ids_and_delete_existing_id_asynchronously(
    session: HTTPSession, async_store: Store
) -> None:
    await async_store.write(
        session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}})
    )

    await session.async_load()

    old_id = session.get_id()

    await session.async_generate_new_id(delete=True)

    assert await async_store.read(old_id) == ""

    assert session.all() == {
        "_csrf_token": session.get_csrf_token(),
        "key": "value",
        "foo": {"bar": "baz"},
    }


def test_session_can_be_regenerated_synchronously(
    session: HTTPSession, store: Store
) -> None:
    store.write(session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}}))

    session.load()

    old_id = session.get_id()
    old_token = session.get_csrf_token()

    session.regenerate(delete=True)

    assert session.get_id() != old_id
    assert session.get_csrf_token() != old_token
    assert store.read(old_id) == ""

    assert session.all() == {
        "_csrf_token": session.get_csrf_token(),
        "key": "value",
        "foo": {"bar": "baz"},
    }


async def test_session_can_be_regenerated_asynchronously(
    session: HTTPSession, async_store: Store
) -> None:
    await async_store.write(
        session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}})
    )

    await session.async_load()

    old_id = session.get_id()
    old_token = session.get_csrf_token()

    await session.async_regenerate(delete=True)

    assert session.get_id() != old_id
    assert session.get_csrf_token() != old_token
    assert await async_store.read(old_id) == ""

    assert session.all() == {
        "_csrf_token": session.get_csrf_token(),
        "key": "value",
        "foo": {"bar": "baz"},
    }


def test_session_can_be_invalidated_synchronously(
    session: HTTPSession, store: Store
) -> None:
    store.write(session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}}))

    session.load()

    old_id = session.get_id()

    session.invalidate()

    assert session.get_id() != old_id
    assert store.read(old_id) == ""

    assert session.all() == {}


async def test_session_can_be_invalidated_asynchronously(
    session: HTTPSession, async_store: AsyncStore
) -> None:
    await async_store.write(
        session.get_id(), json.dumps({"key": "value", "foo": {"bar": "baz"}})
    )

    await session.async_load()

    old_id = session.get_id()

    await session.async_invalidate()

    assert session.get_id() != old_id
    assert await async_store.read(old_id) == ""

    assert session.all() == {}
