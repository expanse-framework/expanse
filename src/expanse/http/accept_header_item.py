"""AcceptHeaderItem facade."""

from __future__ import annotations

from expanse.http._backend import _rust


if _rust is not None:
    AcceptHeaderItem = _rust.AcceptHeaderItem
else:
    from expanse.http._python.accept_header_item import (
        AcceptHeaderItem as _PythonAcceptHeaderItem,
    )

    AcceptHeaderItem = _PythonAcceptHeaderItem  # type: ignore[misc, assignment]


__all__ = ["AcceptHeaderItem"]
