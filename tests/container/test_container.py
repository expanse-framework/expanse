# ruff: noqa: I002
import asyncio
import uuid

from abc import ABC
from abc import abstractmethod
from contextvars import Context
from typing import Any

import pytest

from expanse.container.container import Container
from expanse.support._compat import PY311


class Abstract(ABC):
    @abstractmethod
    def foo(self) -> str:
        ...


class Concrete(Abstract):
    def foo(self) -> str:
        return f"bar {id(self)}"


async def test_singleton_returns_same_instance() -> None:
    """
    Singletons should return the same instance.
    """
    container = Container()
    container.singleton(Abstract, Concrete)

    instance1 = await container.make(Abstract)
    instance2 = await container.make(Abstract)

    assert instance1 is instance2


async def test_concrete_is_resolved_directly() -> None:
    container = Container()

    assert isinstance(await container.make(Concrete), Concrete)


async def test_concrete_is_resolved_directly_and_shared() -> None:
    container = Container()
    container.singleton(Concrete)

    instance1 = await container.make(Concrete)
    instance2 = await container.make(Concrete)

    assert instance1 is instance2


async def test_call_resolves_dependencies() -> None:
    def main(concrete: Abstract, foo: str) -> dict[str, Any]:
        return {"concrete": concrete, "foo": foo}

    container = Container()
    container.singleton(Abstract, Concrete)

    result1 = await container.call(main, "bar")
    result2 = await container.call(main, "baz")

    assert result1["concrete"] == result2["concrete"]
    assert result1["foo"] == "bar"
    assert result2["foo"] == "baz"


async def test_call_async_resolves_dependencies() -> None:
    async def main(concrete: Abstract, foo: str) -> dict[str, Any]:
        return {"concrete": concrete, "foo": foo}

    container = Container()
    container.singleton(Abstract, Concrete)

    result1 = await container.call(main, "bar")
    result2 = await container.call(main, "baz")

    assert result1["concrete"] == result2["concrete"]
    assert result1["foo"] == "bar"
    assert result2["foo"] == "baz"


def test_bound() -> None:
    container = Container()

    assert not container.bound(Abstract)
    container.singleton(Abstract, Concrete)
    assert container.bound(Abstract)


@pytest.mark.skipif(
    not PY311, reason="Passing contexts to asyncio tasks only available for Python 3.11"
)
async def test_scoped_dependencies() -> None:
    async def foo(container: Container) -> str:
        return await container.make("scoped")

    container = Container()
    container.instance(Container, container)
    container.scoped("scoped", lambda _: str(uuid.uuid4()))

    task1 = asyncio.create_task(container.call(foo), context=Context())
    task2 = asyncio.create_task(container.call(foo), context=Context())
    result1 = await task1
    result2 = await task2

    assert result1 != result2
