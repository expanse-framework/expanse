import json

from pathlib import Path

import pytest

from expanse.session.synchronous.stores.file import FileStore


pytestmark = pytest.mark.db


def test_store_can_read_from_the_storage(tmp_path: Path) -> None:
    session_id = "s" * 40

    store = FileStore(tmp_path.joinpath("sessions"), 120)

    assert store.read(session_id) == ""

    tmp_path.joinpath("sessions").mkdir()

    assert store.read(session_id) == ""

    tmp_path.joinpath("sessions").joinpath(session_id).write_text(
        json.dumps({"foo": "bar"})
    )

    assert store.read(session_id) == json.dumps({"foo": "bar"})


def test_store_can_write_data_to_the_storage(tmp_path: Path) -> None:
    session_id = "s" * 40

    store = FileStore(tmp_path.joinpath("sessions"), 120)

    tmp_path.joinpath("sessions").mkdir()

    tmp_path.joinpath("sessions").joinpath(session_id).write_text(
        json.dumps({"foo": "bar"})
    )

    store.write(session_id, json.dumps({"bar": "baz"}))

    assert tmp_path.joinpath("sessions").joinpath(session_id).read_text() == json.dumps(
        {"bar": "baz"}
    )


def test_store_can_delete_sessions(tmp_path: Path) -> None:
    session_id = "s" * 40

    store = FileStore(tmp_path.joinpath("sessions"), 120)

    tmp_path.joinpath("sessions").mkdir()

    tmp_path.joinpath("sessions").joinpath(session_id).write_text(
        json.dumps({"foo": "bar"})
    )

    store.delete(session_id)

    assert not tmp_path.joinpath("sessions").joinpath(session_id).exists()


def test_expired_sessions_can_be_cleared(tmp_path: Path) -> None:
    session_id = "s" * 40

    store = FileStore(tmp_path.joinpath("sessions"), 0)

    tmp_path.joinpath("sessions").mkdir()

    tmp_path.joinpath("sessions").joinpath(session_id).write_text(
        json.dumps({"foo": "bar"})
    )

    assert store.clear() == 1
    assert store.clear() == 0

    assert store.read(session_id) == ""
