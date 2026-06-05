from contextvars import ContextVar

from expanse.logging.context import Context


_context: ContextVar[Context | None] = ContextVar("logging_context", default=None)


def context() -> Context | None:
    return _context.get()


def _set_context(ctx: Context | None) -> None:
    _context.set(ctx)
