import json

import pytest

from expanse.session.synchronous.stores.null import NullStore


pytestmark = pytest.mark.db


def test_store_is_noop() -> None:
    session_id = "s" * 40

    store = NullStore()

    store.write(session_id, json.dumps({"foo": "bar"}))
    assert store.read(session_id) == ""
    assert store.clear() == 0
    store.delete(session_id)
