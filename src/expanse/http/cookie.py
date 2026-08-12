"""Cookie facade — Rust ``Cookie`` / ``SameSite`` when available, Python
fallback under ``expanse.http._python.cookie`` otherwise.
"""

from __future__ import annotations

from expanse.http._backend import _rust
from expanse.http.exceptions import CookieError


if _rust is not None:
    _RustCookie = _rust.Cookie
    # Sentinel that lets us distinguish ``same_site`` omitted from
    # ``same_site=None``. PyO3's ``Option<T>`` signature collapses both to
    # Rust ``None``, so we do the disambiguation on the Python side.
    _SAME_SITE_UNSET: object = object()

    class Cookie(_RustCookie):  # type: ignore[misc, valid-type]
        """Cookie facade with the historical ``same_site=SameSite.LAX``
        default; explicit ``same_site=None`` still means no ``SameSite``
        attribute on the wire.
        """

        def __new__(
            cls,
            name: str,
            value: str | None = None,
            expires: object = 0,
            domain: str | None = None,
            path: str | None = None,
            secure: bool | None = None,
            http_only: bool = False,
            same_site: object = _SAME_SITE_UNSET,
            partitioned: bool = False,
        ) -> Cookie:
            if not name:
                raise CookieError("The cookie name cannot be empty.")
            if same_site is _SAME_SITE_UNSET:
                same_site = _rust.SameSite.LAX  # type: ignore[union-attr]
            return _RustCookie.__new__(  # type: ignore[misc]
                cls,
                name,
                value,
                expires,
                domain,
                path,
                secure,
                http_only,
                same_site,
                partitioned,
            )

    class SameSite:
        """Wrapper around the Rust ``SameSite`` enum that supports the same
        ``SameSite("lax")`` constructor form as ``enum.StrEnum``.

        ``SameSite.LAX``, ``SameSite.STRICT`` and ``SameSite.NONE`` are the
        Rust enum instances directly, so equality with cookies' ``same_site``
        attribute continues to work identically to the pure-Python version.
        """

        LAX = _rust.SameSite.LAX
        STRICT = _rust.SameSite.STRICT
        NONE = _rust.SameSite.NONE

        def __new__(cls, value: str) -> _rust.SameSite:  # type: ignore[misc]
            v = value.lower() if isinstance(value, str) else value
            if v == "lax":
                return cls.LAX
            if v == "strict":
                return cls.STRICT
            if v == "none":
                return cls.NONE
            raise ValueError(f"'{value}' is not a valid SameSite value")

else:
    from expanse.http._python.cookie import Cookie as _PythonCookie
    from expanse.http._python.cookie import SameSite as _PythonSameSite

    Cookie = _PythonCookie  # type: ignore[misc, assignment]
    SameSite = _PythonSameSite  # type: ignore[misc, assignment]


__all__ = ["Cookie", "SameSite"]
