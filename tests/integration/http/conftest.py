from __future__ import annotations

import pytest


@pytest.fixture()
def scope():
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 51715),
        "scheme": "http",
        "root_path": "",
        "headers": [
            (b"host", b"127.0.0.1:8000"),
            (b"accept-encoding", b"gzip, deflate"),
            (b"accept", b"*/*"),
            (b"connection", b"keep-alive"),
            (b"user-agent", b"Foo/3.2.2"),
        ],
        "state": {},
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
    }
