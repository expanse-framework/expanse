from __future__ import annotations

from httpx import Client as BaseClient


class TestClient(BaseClient):
    ...
