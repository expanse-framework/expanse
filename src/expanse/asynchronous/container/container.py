# ruff: noqa: I002
import asyncio
import builtins
import inspect
import logging
import types

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import Self
from typing import TypeVar
from typing import _AnnotatedAlias
from typing import get_args
from typing import overload

from expanse.asynchronous.support._concurrency import run_in_threadpool
from expanse.common.container.container import Container as BaseContainer
from expanse.common.container.exceptions import ResolutionException
from expanse.common.support._utils import string_to_class


T = TypeVar("T")

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_EMPTY = object()

logger = logging.getLogger(__name__)

_Callback = Callable[..., None] | Callable[..., Awaitable[None]]


class UnboundAbstractError(Exception):
    ...


class Container(BaseContainer):
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
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(function, *args)

        if not asyncio.iscoroutinefunction(concrete):
            return await run_in_threadpool(concrete, *positional, **keywords)

        return await concrete(*positional, **keywords)

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
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(callable, *args, **kwargs)

        if asyncio.iscoroutinefunction(callable):
            return await callable(*positional, **keywords)

        return await run_in_threadpool(callable, *positional, **keywords)

    def terminating(
        self,
        callback: _Callback,
        scoped: bool = False,
    ) -> None:
        return super().terminating(callback)

    async def terminate(self) -> None:
        for callback in self._terminating_callbacks:
            await self.call(callback)

    def create_scoped_container(self) -> Self:
        container = ScopedContainer(self)

        return container

    async def on_resolved(
        self,
        abstract: str | type,
        callback: _Callback,
    ) -> None:
        if self.resolved(abstract):
            callback(await self.make(abstract))

        self.after_resolving(abstract, callback)

    def after_resolving(
        self,
        abstract: str | type,
        callback: _Callback,
    ) -> None:
        super().after_resolving(abstract, callback)

    def _concrete_closure(
        self, abstract: str | type, concrete: Any
    ) -> Callable[[Self], Awaitable[Any]]:
        original_concrete = concrete

        async def closure(container: Container) -> Any:
            if abstract == original_concrete:
                return await container.build(original_concrete)

            return await container._resolve(original_concrete)

        return closure

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

    async def _resolve_callable_dependencies(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[list[Any], dict[str, Any]]:
        positional = []
        keywords = {}
        args = list(args)
        _globals = getattr(callable, "__globals__", None)

        for name, parameter in inspect.signature(callable).parameters.items():
            klass = self._get_class(parameter)

            if name == "self":
                continue

            if klass is None:
                await self._resolve_primitive(
                    parameter, args, kwargs, positional, keywords
                )
            else:
                await self._resolve_class(
                    parameter, args, kwargs, positional, keywords, _globals=_globals
                )

        return positional, keywords

    async def _resolve_primitive(
        self,
        parameter: inspect.Parameter,
        args: list[Any],
        kwargs: dict[str, Any],
        positional: list[Any],
        keywords: dict[str, Any],
    ) -> None:
        match parameter.kind:
            case parameter.POSITIONAL_ONLY:
                if not args:
                    raise ResolutionException(
                        f'Unable to resolve dependency with name "{parameter.name}"'
                    )

                positional.append(args.pop(0))

                return

            case parameter.POSITIONAL_OR_KEYWORD:
                # Check in keyword arguments first
                if parameter.name in kwargs:
                    keywords[parameter.name] = kwargs.pop(parameter.name)

                elif args:
                    positional.append(args.pop(0))

                elif parameter.default is not parameter.empty:
                    keywords[parameter.name] = parameter.default

                return

            case parameter.KEYWORD_ONLY:
                if parameter.name in kwargs:
                    keywords[parameter.name] = kwargs.pop(
                        parameter.name,
                    )
                elif parameter.default is not parameter.empty:
                    keywords[parameter.name] = parameter.default

                return

            case parameter.VAR_KEYWORD:
                result = kwargs.copy()

                kwargs.clear()

                keywords.update(result)

                return

            case parameter.VAR_POSITIONAL:
                result = args.copy()

                args.clear()

                result.extend(result)

                return

            case _:
                pass

        raise ResolutionException(
            f'Unable to resolve dependency with name "{parameter.name}"'
        )

    async def _resolve_class(
        self,
        parameter: inspect.Parameter,
        args: list[Any],
        kwargs: dict[str, Any],
        positional: list[Any],
        keywords: dict[str, Any],
        *,
        _globals: dict[str, Any] | None = None,
    ) -> Any:
        match parameter.kind:
            case parameter.POSITIONAL_ONLY:
                klass = self._get_class(parameter, _globals=_globals)

                assert klass is not None

                result = await self.make(self._get_alias(klass))

                positional.append(result)
                return

            case parameter.POSITIONAL_OR_KEYWORD:
                # Check in keyword arguments first
                if parameter.name in kwargs:
                    keywords[parameter.name] = kwargs.pop(parameter.name)
                else:
                    klass = self._get_class(parameter, _globals=_globals)

                    assert klass is not None

                    result = await self.make(self._get_alias(klass))

                    positional.append(result)

                return

            case parameter.KEYWORD_ONLY:
                if parameter.name in kwargs:
                    keywords[parameter.name] = kwargs.pop(
                        parameter.name,
                    )
                else:
                    klass = self._get_class(parameter, _globals=_globals)

                    assert klass is not None

                    result = await self.make(self._get_alias(klass))

                    keywords[parameter.name] = result
                return

            case parameter.VAR_POSITIONAL:
                klass = self._get_class(parameter, _globals=_globals)

                assert klass is not None

                result = await self.make(self._get_alias(klass))

                result = [result] if not isinstance(result, tuple) else result

                positional.extend(result)
                return

            case _:
                pass

        raise ResolutionException(
            f'Unable to resolve dependency with name "{parameter.name}"'
        )

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
            if asyncio.iscoroutinefunction(callback):
                await callback(instance)
            else:
                callback(instance)

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