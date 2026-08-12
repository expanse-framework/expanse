"""Backend selector for the low-level HTTP primitives.

The compiled Rust extension (``expanse._expanse_http``) provides the
performant implementation. If it is unavailable — the extension was not
built, the platform has no wheel, or ``EXPANSE_NO_RUST=1`` is set — the
pure-Python fallback under ``expanse.http._python`` is used instead.

Modules under ``expanse.http`` (``url.py``, ``header_bag.py`` …) import the
``_rust`` object from here and pick their implementation accordingly.

Rust is the source of truth: when Python and Rust behavior diverge, Python
is updated to match Rust rather than the other way around.
"""

from __future__ import annotations

import os


__all__ = ["HAS_RUST", "_rust"]


def _load() -> object | None:
    if os.environ.get("EXPANSE_NO_RUST") == "1":
        return None

    try:
        from expanse import _expanse_http  # type: ignore[attr-defined]
    except ImportError:
        return None

    return _expanse_http


_rust = _load()
HAS_RUST = _rust is not None
