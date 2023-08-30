# ruff: noqa: I002

from abc import ABC
from abc import abstractmethod
from typing import Any

from expanse.container.container import Container


class Abstract(ABC):
    @abstractmethod
    def foo(self) -> str:
        ...


class Concrete(Abstract):
    def foo(self) -> str:
        return f"bar {id(self)}"


def test_singleton_returns_same_instance() -> None:
    """
    Singletons should return the same instance.
    """
    container = Container()
    container.singleton(Abstract, Concrete)

    instance1 = container.make(Abstract)
    instance2 = container.make(Abstract)

    assert instance1 is instance2


def test_concrete_is_resolved_directly() -> None:
    container = Container()

    assert isinstance(container.make(Concrete), Concrete)


def test_concrete_is_resolved_directly_and_shared() -> None:
    container = Container()
    container.singleton(Concrete)

    instance1 = container.make(Concrete)
    instance2 = container.make(Concrete)

    assert instance1 is instance2


def test_call_resolves_dependencies() -> None:
    def main(concrete: Abstract, foo: str) -> dict[str, Any]:
        return {"concrete": concrete, "foo": foo}

    container = Container()
    container.singleton(Abstract, Concrete)

    result1 = container.call(main, "bar")
    result2 = container.call(main, "baz")

    assert result1["concrete"] == result2["concrete"]
    assert result1["foo"] == "bar"
    assert result2["foo"] == "baz"


async def test_call_async_resolves_dependencies() -> None:
    async def main(concrete: Abstract, foo: str) -> dict[str, Any]:
        return {"concrete": concrete, "foo": foo}

    container = Container()
    container.singleton(Abstract, Concrete)

    result1 = await container.call_async(main, "bar")
    result2 = await container.call_async(main, "baz")

    assert result1["concrete"] == result2["concrete"]
    assert result1["foo"] == "bar"
    assert result2["foo"] == "baz"


def test_bound() -> None:
    container = Container()

    assert not container.bound(Abstract)
    container.singleton(Abstract, Concrete)
    assert container.bound(Abstract)
