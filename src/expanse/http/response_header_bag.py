"""ResponseHeaderBag facade.

Same pattern as :mod:`expanse.http.header_bag` — pick the Rust
implementation when available, fall back to
``expanse.http._python.response_header_bag``.
"""

from __future__ import annotations

from collections.abc import MutableMapping

from expanse.http._backend import _rust
from expanse.http.header_bag import HeaderBag


if _rust is not None:
    _ResponseHeaderBagBase = _rust.ResponseHeaderBag

    class ResponseHeaderBag(  # type: ignore[misc, valid-type]
        _ResponseHeaderBagBase, HeaderBag, MutableMapping[str, str]
    ):
        pass

else:
    from expanse.http._python.response_header_bag import (
        ResponseHeaderBag as _PythonResponseHeaderBag,
    )

    ResponseHeaderBag = _PythonResponseHeaderBag  # type: ignore[misc, assignment]


__all__ = ["ResponseHeaderBag"]
