"""URLPath facade.

``URLPath`` is a ``str`` subclass, which is awkward to expose from Rust,
so the Python implementation is the source of truth for this type. The
facade exists to keep the public import path (``expanse.http.url_path``)
stable now that internal Python code lives under ``_python/``.
"""

from expanse.http._python.url_path import URLPath


__all__ = ["URLPath"]
