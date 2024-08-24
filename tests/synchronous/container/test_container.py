# ruff: noqa: I002
import uuid

from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from expanse.container.container import Container


class Something: ...


class AnotherThing:
    def __init__(self, value: str) -> None:
        self.value = value


class Abstract(ABC):
    @abstractmethod
    def foo(self) -> str: ...

    @abstractmethod
    def run(
        self, foo: str, bar: str, baz: str | None = None
    ) -> tuple[str, str, str | None]: ...

    @abstractmethod
    def run2(
        self, something: Something, foo: str, bar: str, baz: str | None = None
    ) -> tuple[str, str, str | None]: ...

    @abstractmethod
    def run3(
        self,
        something: Something,
        another_thing: AnotherThing,
        foo: str,
        callback: Callable[[int], int],
        bar: str,
        baz: str | None = None,
    ) -> tuple[str, str, int, str, str | None]: ...


class Concrete(Abstract):
    def foo(self) -> str:
        return f"bar {id(self)}"

    def run(
        self, foo: str, bar: str, baz: str | None = None
    ) -> tuple[str, str, str | None]:
        return foo, bar, baz

    def run2(
        self, something: Something, foo: str, bar: str, baz: str | None = None
    ) -> tuple[str, str, str | None]:
        return foo, bar, baz

    def run3(
        self,
        something: Something,
        another_thing: AnotherThing,
        foo: str,
        callback: Callable[[int], int],
        bar: str,
        baz: str | None = None,
    ) -> tuple[str, str, int, str, str | None]:
        return foo, another_thing.value, callback(3), bar, baz


class Foo:
    def __init__(self, concrete: Abstract) -> None:
        self.concrete = concrete
        self._id = str(uuid.uuid4())

    def get_id(self) -> str:
        return self._id


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


def test_call_resolves_dependencies_and_parameters_if_parameters_only() -> None:
    container = Container()
    container.singleton(Abstract, Concrete)

    concrete = container.make(Abstract)

    result = container.call(concrete.run, "foo", "bar")
    assert result == ("foo", "bar", None)

    result = container.call(concrete.run, "foo", "bar", baz="baz")
    assert result == ("foo", "bar", "baz")


def test_call_resolves_deps_and_params_with_mix_of_deps_and_params() -> None:
    container = Container()
    container.singleton(Abstract, Concrete)
    container.singleton(Something)

    concrete = container.make(Abstract)

    result = container.call(concrete.run2, "foo", "bar")
    assert result == ("foo", "bar", None)

    result = container.call(concrete.run2, "foo", "bar", baz="baz")
    assert result == ("foo", "bar", "baz")


def test_call_resolves_dependencies_and_parameters_with_any_parameter_type() -> None:
    container = Container()
    container.singleton(Abstract, Concrete)
    container.singleton(Something)

    def callback(i: int) -> int:
        return i

    concrete = container.make(Abstract)

    result = container.call(
        concrete.run3, AnotherThing("Value 1"), "foo", callback, "bar"
    )
    assert result == ("foo", "Value 1", 3, "bar", None)

    result = container.call(
        concrete.run3, AnotherThing("Value 2"), "foo", callback, "bar", baz="baz"
    )
    assert result == ("foo", "Value 2", 3, "bar", "baz")


def test_call_can_call_instance_methods() -> None:
    container = Container()
    container.instance(Container, container)
    container.bind(Abstract, Concrete)

    id1 = container.call(Foo.get_id)

    assert isinstance(id1, str)

    id2 = container.call(Foo.get_id)

    assert isinstance(id2, str)
    assert id1 != id2

    container.singleton(Foo)
    container.make(Foo)

    assert container.call(Foo.get_id) == container.call(Foo.get_id)
