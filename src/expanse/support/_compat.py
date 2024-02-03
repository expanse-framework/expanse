from __future__ import annotations

import hashlib
import sys

from typing import Any
from typing import AsyncContextManager


PY310 = sys.version_info >= (3, 10)
PY311 = sys.version_info >= (3, 11)

if PY310:  # pragma: no cover
    from contextlib import aclosing
else:  # pragma: no cover

    class aclosing(AsyncContextManager):  # noqa: N801
        def __init__(self, thing: Any) -> None:
            self.thing = thing

        async def __aenter__(self) -> Any:
            return self.thing

        async def __aexit__(self, *exc_info: Any) -> None:
            await self.thing.aclose()


# Compat wrapper to always include the `usedforsecurity=...` parameter,
# which is only added from Python 3.9 onwards.
# We use this flag to indicate that we use `md5` hashes only for non-security
# cases (our ETag checksums).
# If we don't indicate that we're using MD5 for non-security related reasons,
# then attempting to use this function will raise an error when used
# environments which enable a strict "FIPs mode".
#
# See issue: https://github.com/encode/starlette/issues/1365
try:
    # check if the Python version supports the parameter
    # using usedforsecurity=False to avoid an exception on FIPS systems
    # that reject usedforsecurity=True
    hashlib.md5(b"data", usedforsecurity=False)  # type: ignore[call-arg]

    def md5_hexdigest(
        data: bytes, *, usedforsecurity: bool = True
    ) -> str:  # pragma: no cover
        return hashlib.md5(  # type: ignore[call-arg]
            data, usedforsecurity=usedforsecurity
        ).hexdigest()

except TypeError:  # pragma: no cover

    def md5_hexdigest(data: bytes, *, usedforsecurity: bool = True) -> str:
        return hashlib.md5(data).hexdigest()
