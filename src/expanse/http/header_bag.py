"""HeaderBag facade.

Rust implementation lives in ``expanse._expanse_http.HeaderBag``; the
pure-Python fallback sits at ``expanse.http._python.header_bag.HeaderBag``.
The public class picks whichever backend is available and mixes in
``MutableMapping`` so callers get ``update``, ``setdefault``, ``pop`` etc.
for free on top of the Rust mapping protocol methods.
"""

from __future__ import annotations

from collections.abc import MutableMapping

from expanse.http._backend import _rust


if _rust is not None:
    _HeaderBagBase = _rust.HeaderBag

    class HeaderBag(_HeaderBagBase, MutableMapping[str, str]):  # type: ignore[misc, valid-type]
        pass

else:
    from expanse.http._python.header_bag import HeaderBag as _PythonHeaderBag

    HeaderBag = _PythonHeaderBag  # type: ignore[misc, assignment]


__all__ = ["HeaderBag"]
