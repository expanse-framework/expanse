import asyncio

from collections.abc import Awaitable
from collections.abc import Callable
from contextvars import ContextVar

from sqlalchemy.util.concurrency import await_only

from expanse.support._concurrency import run_in_threadpool


Callback = Callable[[], None] | Callable[[], Awaitable[None]]


after_commit_callbacks: ContextVar[list[Callback] | None] = ContextVar(
    "after_commit_callbacks", default=None
)


def add_after_commit_callback(callback: Callback) -> None:
    callbacks: list[Callback] | None = after_commit_callbacks.get()
    if callbacks is None:
        callbacks = []

    callbacks.append(callback)
    after_commit_callbacks.set(callbacks)


async def execute_after_commit_callbacks(_) -> None:
    callbacks = after_commit_callbacks.get()
    if not callbacks:
        return None

    after_commit_callbacks.set(None)

    for callback in callbacks:
        if asyncio.iscoroutinefunction(callback):
            await callback()
        else:
            await run_in_threadpool(callback)


def execute_after_commit_callbacks_sync(_) -> None:
    callbacks = after_commit_callbacks.get()
    if not callbacks:
        return None

    after_commit_callbacks.set(None)

    for callback in callbacks:
        if asyncio.iscoroutinefunction(callback):
            await_only(callback())
        else:
            callback()
