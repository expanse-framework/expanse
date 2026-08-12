"""AcceptHeader facade."""

from __future__ import annotations

from expanse.http._backend import _rust


if _rust is not None:
    AcceptHeader = _rust.AcceptHeader
else:
    from expanse.http._python.accept_header import AcceptHeader as _PythonAcceptHeader

    AcceptHeader = _PythonAcceptHeader  # type: ignore[misc, assignment]


__all__ = ["AcceptHeader"]
