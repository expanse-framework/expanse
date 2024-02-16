import httpx

from expanse.common.testing.client import TestClient as BaseTestClient
from expanse.foundation.application import Application


class TestClient(BaseTestClient):
    def __init__(
        self,
        app: Application,
        base_url: str = "http://testserver",
        cookies: httpx._client.CookieTypes = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.app = app
        if headers is None:
            headers = {}

        headers.setdefault("user-agent", "testclient")
        super().__init__(
            app=self.app,
            base_url=base_url,
            headers=headers,
            follow_redirects=True,
            cookies=cookies,
        )
