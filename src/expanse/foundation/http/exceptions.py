from __future__ import annotations

from starlette.exceptions import HTTPException as BaseHTTPException


class HTTPException(BaseHTTPException):
    ...
