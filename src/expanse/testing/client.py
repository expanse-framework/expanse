import contextlib

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
        if headers is None:
            headers = {}

        headers.setdefault("user-agent", "testclient")
        super().__init__(
            app=app,
            base_url=base_url,
            headers=headers,
            follow_redirects=True,
            cookies=cookies,
        )

    @property
    def transport(self) -> httpx.WSGITransport:
        return httpx.WSGITransport(app=self.app, raise_app_exceptions=True)

    @contextlib.contextmanager
    def handle_exceptions(
        self, handle_exceptions: bool = True
    ) -> contextlib.AbstractContextManager[None]:
        raise_app_exceptions = self.transport.raise_app_exceptions
        self.transport.raise_app_exceptions = not handle_exceptions

        yield

        self.transport.raise_app_exceptions = raise_app_exceptions
