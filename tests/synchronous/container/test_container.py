# ruff: noqa: I002
import uuid

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


def test_bound() -> None:
    container = Container()

    assert not container.bound(Abstract)
    container.singleton(Abstract, Concrete)
    assert container.bound(Abstract)


def test_scoped_dependencies() -> None:
    def foo(container: Container) -> str:
        return container.make("scoped")

    container = Container()
    container.instance(Container, container)
    container.scoped("scoped", lambda _: str(uuid.uuid4()))

    assert container.has_scoped_bindings()

    with container.create_scoped_container() as c1:
        result1 = c1.make("scoped")
        result2 = c1.make("scoped")

    with container.create_scoped_container() as c2:
        result3 = c2.make("scoped")

    assert result1 == result2
    assert result1 != result3


def test_scoped_container_can_resolve_base_container_dependencies() -> None:
    container = Container()
    container.instance(Container, container)
    container.bind(Abstract, Concrete)
    container.scoped(uuid.UUID, uuid.uuid4)

    scoped = container.create_scoped_container()

    result = scoped.make(Abstract)

    assert isinstance(result, Concrete)
