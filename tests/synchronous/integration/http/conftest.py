from __future__ import annotations

import pytest


@pytest.fixture()
def environ():
    return {
        "REQUEST_METHOD": "GET",
        "SCRIPT_NAME": "",
        "PATH_INFO": "/",
        "HTTP_HOST": "127.0.0.1:8000",
        "HTTP_ACCEPT_ENCODING": "gzip, deflate",
        "HTTP_ACCEPT": "*/*",
        "HTTP_CONNECTION": "127.0.0.1:8000",
        "HTTP_USER_AGENT": "127.0.0.1:8000",
        "QUERY_STRING": "",
    }
