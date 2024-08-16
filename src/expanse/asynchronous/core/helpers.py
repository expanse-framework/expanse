from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from expanse.asynchronous.container.container import Container

_container: ContextVar[Container | None] = ContextVar("container", default=None)


def _get_container() -> Container:
    container = _container.get()

    if container is None:
        raise RuntimeError("Container not set.")

    return container


def _set_container(container: Container | None) -> None:
    _container.set(container)


@asynccontextmanager
async def _use_container(
    container: Container,
) -> AsyncGenerator[Container]:
    _set_container(container)

    yield container

    _set_container(None)
