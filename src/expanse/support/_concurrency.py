from __future__ import annotations

import asyncio
import functools

from collections import deque
from collections.abc import AsyncGenerator
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from contextvars import Context
from contextvars import copy_context
from typing import ParamSpec
from typing import TypeVar

import anyio.to_thread


P = ParamSpec("P")
T = TypeVar("T")


def _restore_context(context: Context) -> None:
    """
    Copy the state of `context` to the current context.
    """
    for cvar in context:
        new_val = context.get(cvar)
        try:
            if cvar.get() != new_val:
                cvar.set(new_val)
        except LookupError:
            # the context variable was first set inside `context`
            cvar.set(new_val)


async def run_in_threadpool(
    func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    if kwargs:  # pragma: no cover
        # run_sync doesn't accept 'kwargs', so bind them in here
        func = functools.partial(func, **kwargs)

    context = copy_context()
    func = functools.partial(context.run, func)

    result = await anyio.to_thread.run_sync(func, *args)

    if context is not None:
        # restore the context
        _restore_context(context)

    return result


class AsyncIteratorWrapper[T]:
    __slots__ = ("generator", "iterator")

    def __init__(self, iterator: Iterator[T] | Iterable[T]) -> None:
        """Take a sync iterator or iterable and yields values from it asynchronously.

        Args:
            iterator: A sync iterator or iterable.
        """
        self.iterator = iterator if isinstance(iterator, Iterator) else iter(iterator)
        self.generator = self._async_generator()

    def _call_next(self) -> T:
        try:
            return next(self.iterator)
        except StopIteration as e:
            raise ValueError from e

    async def _async_generator(self) -> AsyncGenerator[T, None]:
        while True:
            try:
                yield await run_in_threadpool(self._call_next)
            except ValueError:
                return

    def __aiter__(self) -> AsyncIteratorWrapper[T]:
        return self

    async def __anext__(self) -> T:
        return await self.generator.__anext__()


class AsyncRLock:
    """
    A reentrant lock for async programming.

    Original implementation: https://github.com/Joshuaalbert/FairAsyncRLock
    """

    def __init__(self):
        self._owner: asyncio.Task | None = None
        self._count = 0
        self._owner_transfer = False
        self._queue = deque()

    def is_owner(self, task=None):
        if task is None:
            task = asyncio.current_task()
        return self._owner == task

    def locked(self) -> bool:
        return self._owner is not None

    async def acquire(self):
        """Acquire the lock."""
        me = asyncio.current_task()

        # If the lock is reentrant, acquire it immediately
        if self.is_owner(task=me):
            self._count += 1
            return

        # If the lock is free (and ownership not in midst of transfer), acquire it immediately
        if self._count == 0 and not self._owner_transfer:
            self._owner = me
            self._count = 1
            return

        # Create an event for this task, to notify when it's ready for acquire
        event = asyncio.Event()
        self._queue.append(event)

        # Wait for the lock to be free, then acquire
        try:
            await event.wait()
            self._owner_transfer = False
            self._owner = me
            self._count = 1
        except asyncio.CancelledError:
            try:  # if in queue, then cancelled before release
                self._queue.remove(event)
            except (
                ValueError
            ):  # otherwise, release happened, this was next, and we simulate passing on
                self._owner_transfer = False
                self._owner = me
                self._count = 1
                self._current_task_release()
            raise

    def _current_task_release(self):
        self._count -= 1
        if self._count == 0:
            self._owner = None
            if self._queue:
                # Wake up the next task in the queue
                event = self._queue.popleft()
                event.set()
                # Setting this here prevents another task getting lock until owner transfer.
                self._owner_transfer = True

    def release(self):
        """Release the lock"""
        me = asyncio.current_task()

        if self._owner is None:
            raise RuntimeError(
                f"Cannot release un-acquired lock. {me} tried to release."
            )

        if not self.is_owner(task=me):
            raise RuntimeError(
                f"Cannot release foreign lock. {me} tried to unlock {self._owner}."
            )

        self._current_task_release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.release()
