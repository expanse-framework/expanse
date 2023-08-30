from __future__ import annotations

from starlette.testclient import TestClient as BaseTestClient


class TestClient(BaseTestClient):
    ...
