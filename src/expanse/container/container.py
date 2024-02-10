# ruff: noqa: I002
import asyncio
import builtins
import inspect
import logging
import types

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from inspect import Parameter
from typing import Any
from typing import Self
from typing import TypeVar
from typing import _AnnotatedAlias
from typing import get_args
from typing import overload

from starlette.concurrency import run_in_threadpool

from expanse.support._utils import string_to_class


T = TypeVar("T")

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_EMPTY = object()

logger = logging.getLogger(__name__)


class UnboundAbstractError(Exception):
    ...


class Container:
    def __init__(self) -> None:
        self._bindings: dict[str | type, Any] = {}
        self._resolved: dict[str | type, bool] = {}
        self._instances: dict[str | type, Any] = {}
        self._aliases: dict[str, str | type] = {}

        self._scoped_bindings: dict[str, Any] = {}

        self._after_resolving_callbacks: dict[
            str | type, list[Callable[..., None] | Callable[..., Awaitable[None]]]
        ] = defaultdict(list)

        self._terminating_callbacks: list[
            Callable[..., None] | Callable[..., Awaitable[None]]
        ] = []

        self._scoped_terminating_callbacks: list[
            Callable[..., None] | Callable[..., Awaitable[None]]
        ] = []

    def bind(
        self,
        abstract: type | str,
        concrete: Any = None,
        *,
        cached: bool = False,
        scoped: bool = False,
    ) -> None:
        if concrete is None:
            concrete = abstract

        if not isinstance(concrete, types.FunctionType | types.MethodType):
            original_concrete = concrete

            async def _container_concrete(container: Container) -> Any:
                if abstract == original_concrete:
                    return await container.build(original_concrete)

                return await container._resolve(original_concrete)

            concrete = _container_concrete

        if scoped:
            self._scoped_bindings[abstract] = {"concrete": concrete, "cached": cached}
        else:
            self._bindings[abstract] = {"concrete": concrete, "cached": cached}

    def singleton(
        self, abstract: type | str, concrete: Any = None, *, scoped: bool = False
    ) -> None:
        self.bind(abstract, concrete, cached=True, scoped=scoped)

    def scoped(self, abstract: type | str, concrete: Any = None) -> None:
        self.singleton(abstract, concrete, scoped=True)

    def instance(
        self, abstract: type | str, instance: Any, scoped: bool = False
    ) -> None:
        self._instances[abstract] = instance

    async def build(self, concrete: type | str, args: tuple | None = None) -> Any:
        if args is None:
            args = ()

        if isinstance(concrete, types.FunctionType):
            if concrete.__name__ == "<lambda>":
                return concrete(self, *args)

            if concrete.__name__ == "_container_concrete":
                return await concrete(self)

            function = concrete
        elif isinstance(concrete, types.MethodType):
            function = concrete
        else:
            if isinstance(concrete, str):
                concrete = string_to_class(concrete)

            if isinstance(concrete, types.MethodType):
                function = concrete
            else:
                function = concrete.__init__  # type: ignore[misc]

        (
            resolved_positional,
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(function)

        positional = list(args) + positional[len(args) :]

        if not asyncio.iscoroutinefunction(concrete):
            return await run_in_threadpool(
                concrete, *resolved_positional, *positional, **keywords
            )

        return await concrete(*resolved_positional, *positional, **keywords)

    @overload
    async def make(self, abstract: type[T]) -> T:
        ...

    @overload
    async def make(self, abstract: str) -> Any:
        ...

    async def make(self, abstract: str | type[T]) -> Any | T:
        return await self._resolve(abstract)

    async def call(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        (
            resolved_positional,
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(callable)

        positional = list(args) + positional[len(args) :]

        if asyncio.iscoroutinefunction(callable):
            return await callable(
                *resolved_positional, *positional, **{**keywords, **kwargs}
            )

        return await run_in_threadpool(
            callable, *resolved_positional, *positional, **{**keywords, **kwargs}
        )

    def alias(self, abstract: str | type, alias: str) -> None:
        self._aliases[alias] = abstract

    def bound(self, abstract: str | type) -> bool:
        return abstract in self._bindings or abstract in self._instances

    def terminating(
        self,
        callback: Callable[..., None] | Callable[..., Awaitable[None]],
        scoped: bool = False,
    ) -> None:
        if scoped:
            self._scoped_terminating_callbacks.append(callback)
        else:
            self._terminating_callbacks.append(callback)

    async def terminate(self) -> None:
        for callback in self._terminating_callbacks:
            await self.call(callback)

    def create_scoped_container(self) -> Self:
        container = ScopedContainer(self)

        return container

    def has_scoped_bindings(self) -> bool:
        return bool(self._scoped_bindings)

    def resolved(self, abstract: str | type) -> bool:
        abstract = self._get_alias(abstract)

        return self._resolved.get(abstract, False)

    def on_resolved(
        self,
        abstract: str | type,
        callback: Callable[..., None] | Callable[..., Awaitable[None]],
    ) -> None:
        if self.resolved(abstract):
            callback(self.make(abstract))

        self.after_resolving(abstract, callback)

    def after_resolving(
        self,
        abstract: str | type,
        callback: Callable[..., None] | Callable[..., Awaitable[None]],
    ) -> None:
        abstract = self._get_alias(abstract)

        actual_abstract: str | type[T] = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *_ = get_args(abstract)

        if abstract in self._bindings:
            self._after_resolving_callbacks[abstract].append(callback)
        elif actual_abstract in self._bindings:
            self._after_resolving_callbacks[actual_abstract].append(callback)
        else:
            self._after_resolving_callbacks[abstract].append(callback)

    @overload
    async def _resolve(self, abstract: type[T]) -> T:
        ...

    @overload
    async def _resolve(self, abstract: str) -> Any:
        ...

    async def _resolve(self, abstract: str | type[T]) -> Any | T:
        abstract = self._get_alias(abstract)

        if abstract in self._instances:
            return self._instances[abstract]

        metadata: tuple = ()
        actual_abstract: str | type[T] = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *metadata = get_args(abstract)

        if actual_abstract in self._bindings:
            concrete = self._bindings[actual_abstract]["concrete"]
        elif isinstance(abstract, str):
            # Unbound strings cannot be resolved
            raise UnboundAbstractError(
                f"Unbound abstract [{abstract}] cannot be resolved"
            )
        else:
            concrete = abstract

        if self._is_buildable(actual_abstract, concrete):
            try:
                obj = await self.build(concrete, metadata)
            except Exception:
                logger.exception('Unable to build the "%s" dependency', abstract)

                raise
        else:
            obj = await self.make(concrete)

        if self._is_cached(actual_abstract):
            self._instances[abstract] = obj

        self._mark_as_resolved(actual_abstract)

        await self._execute_after_resolving_callbacks(abstract, obj)

        return obj

    def _is_buildable(self, abstract: str, concrete: Any) -> bool:
        return abstract == concrete or isinstance(
            concrete, types.FunctionType | types.MethodType
        )

    def _is_cached(self, abstract: str) -> bool:
        return abstract in self._instances or self._bindings.get(abstract, {}).get(
            "cached", False
        )

    def _mark_as_resolved(self, abstract: str) -> None:
        self._resolved[abstract] = True

    async def _resolve_callable_dependencies(
        self, callable: Callable[..., Any]
    ) -> tuple[list[Any], list[Any], dict[str, Any]]:
        resolved_positional = []
        positional = []
        keywords = {}

        for name, parameter in inspect.signature(callable).parameters.items():
            resolved = False
            klass = self._get_class(parameter)

            if name == "self":
                continue

            if klass is None:
                result = await self._resolve_primitive(parameter)
            else:
                try:
                    result = await self._resolve_class(parameter)
                except Exception:
                    continue

                resolved = True

            if result is _EMPTY:
                continue

            if parameter.kind in (
                parameter.POSITIONAL_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
            ):
                if resolved:
                    resolved_positional.append(result)
                else:
                    positional.append(result)
            elif parameter.kind == parameter.KEYWORD_ONLY:
                keywords[parameter.name] = result
            if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                if resolved:
                    resolved_positional.append(result)
                else:
                    positional.append(result)
            elif parameter.kind == inspect.Parameter.VAR_KEYWORD:
                keywords.update(result)

        return resolved_positional, positional, keywords

    async def _resolve_primitive(self, parameter: inspect.Parameter) -> Any:
        if parameter.default is not parameter.empty:
            return parameter.default

        return _EMPTY

    async def _resolve_class(self, parameter: inspect.Parameter) -> Any:
        klass = self._get_class(parameter)

        assert klass is not None

        return await self.make(self._get_alias(klass))

    def _get_class(self, parameter: Parameter) -> type | None:
        type_ = parameter.annotation

        if type_ is Parameter.empty:
            return None

        if isinstance(type_, types.UnionType):
            # Get the first type of the type union
            type_ = get_args(type_)[0]

        if inspect.getmodule(type_) == builtins:
            return None

        return type_

    def _get_alias(self, abstract: str | type) -> str:
        return self._aliases.get(abstract, abstract)

    async def _execute_after_resolving_callbacks(
        self, abstract: str | type, instance: Any
    ) -> None:
        callbacks: list[Callable[..., Awaitable[None]]] = []
        abstract = self._get_alias(abstract)

        actual_abstract: str | type[T] = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *_ = get_args(abstract)

        if abstract in self._after_resolving_callbacks:
            callbacks += self._after_resolving_callbacks[abstract]

        if actual_abstract in self._after_resolving_callbacks[actual_abstract]:
            callbacks += self._after_resolving_callbacks[actual_abstract]

        for callback in callbacks:
            if self._is_lambda(callback):
                callback(instance)

                continue

            await self.call(callback)

    def _is_lambda(
        self, callable: Callable[..., None] | Callable[..., Awaitable[None]]
    ) -> None:
        return (
            isinstance(callable, types.FunctionType) and callable.__name__ == "<lambda>"
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.terminate()


class ScopedContainer(Container):
    def __init__(self, base_container: Container):
        super().__init__()

        self._base_container = base_container

        # Bind scoped bindings from the base container
        self._bindings.update(
            {k: {**v} for k, v in self._base_container._scoped_bindings.items()}
        )

        # Setup terminating callbacks
        self._terminating_callbacks = [
            *self._base_container._scoped_terminating_callbacks
        ]

        self.instance(Container, self)

    def bound(self, abstract: str | type) -> bool:
        return self._base_container.bound(abstract) or super().bound(abstract)

    def _directly_bound(self, abstract: str | type) -> bool:
        return super().bound(abstract)

    async def _resolve(self, abstract: str | type[T]) -> Any | T:
        actual_abstract: str | type[T] = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *_ = get_args(abstract)

        if not self._directly_bound(actual_abstract):
            return await self._base_container._resolve(abstract)

        return await super()._resolve(abstract)
