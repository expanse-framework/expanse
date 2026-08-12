"""Facade over ``expanse.http._python._datastructures``.

Only ``ContentType`` has a Rust implementation right now; the other
value types (Address, QueryParams, CookieJar, RawUploadFile, FormData)
either subclass Python-only mixins or wrap ``SpooledTemporaryFile``, so
they stay in Python.
"""

from __future__ import annotations

from expanse.http._backend import _rust
from expanse.http._python._datastructures import Address
from expanse.http._python._datastructures import CookieJar
from expanse.http._python._datastructures import FormData
from expanse.http._python._datastructures import QueryParams
from expanse.http._python._datastructures import RawUploadFile


if _rust is not None:
    ContentType = _rust.ContentType
else:
    from expanse.http._python._datastructures import ContentType as _PythonContentType

    ContentType = _PythonContentType  # type: ignore[misc, assignment]


__all__ = [
    "Address",
    "ContentType",
    "CookieJar",
    "FormData",
    "QueryParams",
    "RawUploadFile",
]
