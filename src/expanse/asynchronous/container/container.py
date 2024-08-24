# ruff: noqa: I002
import asyncio
import builtins
import inspect
import logging
import types

from collections.abc import Awaitable
from collections.abc import Callable
from inspect import isasyncgenfunction
from inspect import isgeneratorfunction
from typing import Any
from typing import Self
from typing import TypeVar
from typing import _AnnotatedAlias  # type: ignore[attr-defined]
from typing import get_args
from typing import overload

from expanse.asynchronous.support._concurrency import run_in_threadpool
from expanse.common.container.container import Container as BaseContainer
from expanse.common.container.exceptions import ContainerException
from expanse.common.container.exceptions import ResolutionException
from expanse.common.container.exceptions import UnboundAbstractException
from expanse.common.support._utils import string_to_class


T = TypeVar("T")

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_EMPTY = object()

logger = logging.getLogger(__name__)

_Callback = Callable[..., None] | Callable[..., Awaitable[None]]


class UnboundAbstractError(Exception): ...


class Container(BaseContainer):
    def __init__(self) -> None:
        super().__init__()

        self._terminating_callbacks: list[_Callback] = []
        self._scoped_terminating_callbacks: list[_Callback] = []

    async def build(
        self, concrete: type | str, args: tuple | None = None
    ) -> tuple[Any, _Callback | None]:
        if args is None:
            args = ()

        function: Callable[..., Any]
        if isinstance(concrete, types.FunctionType):
            if concrete.__name__ == "<lambda>":
                return concrete(self, *args), None

            if concrete.__name__ == "_container_concrete":
                return await concrete(self), None

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

        if isasyncgenfunction(concrete):
            generator = concrete(*positional, **keywords)

            async def terminating_callback() -> None:
                await anext(generator, None)

            return await anext(generator), terminating_callback

        if isgeneratorfunction(concrete):
            generator = concrete(*positional, **keywords)

            def sync_terminating_callback() -> None:
                next(generator, None)

            return next(generator), sync_terminating_callback

        if not asyncio.iscoroutinefunction(concrete):
            return await run_in_threadpool(concrete, *positional, **keywords), None

        return await concrete(*positional, **keywords), None

    @overload
    async def make(self, abstract: type[T]) -> T: ...

    @overload
    async def make(self, abstract: str) -> Any: ...

    async def make(self, abstract: str | type[T]) -> Any | T:
        return await self._resolve(abstract)

    async def call(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        if (
            isinstance(callable, types.FunctionType)
            and "." in callable.__qualname__
            and not inspect.ismethod(callable)
            and "<locals>" not in callable.__qualname__
        ):
            # We have an instance method, so we will retrieve the corresponding class,
            # resolve it and call the method.
            class_name, func_name = callable.__qualname__.rsplit(".", maxsplit=1)
            class_: type = callable.__globals__[class_name]

            instance: Any = await self.make(class_)

            callable = getattr(instance, func_name)

        (
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(callable, *args, **kwargs)

        if asyncio.iscoroutinefunction(callable):
            return await callable(*positional, **keywords)

        return await run_in_threadpool(callable, *positional, **keywords)

    def terminating(self, callback: _Callback, scoped: bool = False) -> None:
        if scoped:
            self._scoped_terminating_callbacks.append(callback)
        else:
            self._terminating_callbacks.append(callback)

    async def terminate(self) -> None:
        for callback in self._terminating_callbacks:
            await self.call(callback)

    def create_scoped_container(self) -> "ScopedContainer":
        container = ScopedContainer(self)

        return container

    async def on_resolved(
        self,
        abstract: str | type,
        callback: _Callback,
    ) -> None:
        if self.resolved(abstract):
            if asyncio.iscoroutinefunction(callback):
                await callback(await self.make(abstract))
            else:
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
                obj, _ = await container.build(original_concrete)

                return obj

            return await container._resolve(original_concrete)

        return closure

    @overload
    async def _resolve(self, abstract: type[T]) -> T: ...

    @overload
    async def _resolve(self, abstract: str) -> Any: ...

    async def _resolve(self, abstract: str | type[T]) -> Any | T:
        abstract = self._get_alias(abstract)

        if abstract in self._instances:
            return self._instances[abstract]

        metadata: tuple = ()
        actual_abstract: str | type = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *metadata = get_args(abstract)  # type: ignore[assignment]

        if actual_abstract in self._bindings:
            concrete = self._bindings[actual_abstract]["concrete"]
        elif isinstance(abstract, str):
            # Unbound strings cannot be resolved
            raise UnboundAbstractException(
                f"Unbound abstract [{abstract}] cannot be resolved"
            )
        else:
            concrete = abstract

        terminating_callback: _Callback | None = None
        if self._is_buildable(actual_abstract, concrete):
            try:
                obj, terminating_callback = await self.build(concrete, metadata)
            except Exception:
                raise ContainerException(f'Unable to build the "{abstract}" dependency')
        else:
            obj = await self.make(concrete)

        if self._is_cached(actual_abstract):
            self._instances[abstract] = obj

        self._mark_as_resolved(actual_abstract)
        if terminating_callback is not None:
            self.terminating(terminating_callback)

        await self._execute_after_resolving_callbacks(abstract, obj)

        return obj

    async def _resolve_callable_dependencies(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[list[Any], dict[str, Any]]:
        positional: list[Any] = []
        keywords: dict[str, Any] = {}
        arguments = list(args)
        _globals = getattr(callable, "__globals__", None)

        for name, parameter in inspect.signature(callable).parameters.items():
            klass = self._get_class(parameter)

            if name == "self":
                continue

            if klass is None:
                await self._resolve_primitive(
                    parameter, arguments, kwargs, positional, keywords
                )
            else:
                try:
                    await self._resolve_class(
                        parameter,
                        arguments,
                        kwargs,
                        positional,
                        keywords,
                        _globals=_globals,
                    )
                except ContainerException as e:
                    raise ResolutionException(
                        f'Unable to resolve dependency with name "{parameter.name}" '
                        f'(type: {klass.__module__ + "." + klass.__qualname__}) '
                        f'in "{callable.__module__ + "." + callable.__qualname__}"'
                    ) from e

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
                keywords.update(kwargs.copy())

                kwargs.clear()

                return

            case parameter.VAR_POSITIONAL:
                positional.extend(args.copy())

                args.clear()

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

                if self.has(self._get_alias(klass)):
                    result = await self.make(self._get_alias(klass))
                else:
                    try:
                        result = await self.make(self._get_alias(klass))
                    except Exception as e:
                        if not args:
                            raise e

                        arg = args[0]

                        if not isinstance(arg, klass):
                            raise e

                        result = args.pop(0)

                positional.append(result)
                return

            case parameter.POSITIONAL_OR_KEYWORD:
                # Check in keyword arguments first
                if parameter.name in kwargs:
                    keywords[parameter.name] = kwargs.pop(parameter.name)
                else:
                    klass = self._get_class(parameter, _globals=_globals)

                    assert klass is not None

                    if self.has(self._get_alias(klass)):
                        result = await self.make(self._get_alias(klass))
                    else:
                        try:
                            result = await self.make(self._get_alias(klass))
                        except Exception as e:
                            if not args:
                                raise e

                            arg = args[0]

                            if not isinstance(arg, klass):
                                raise e

                            result = args.pop(0)

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

        actual_abstract: str | type = abstract
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

        # If the abstract is neither bound in the container nor in its base container,
        # we will resolve it from the scoped container.
        if not self.bound(abstract):
            return await super()._resolve(abstract)

        if not self._directly_bound(actual_abstract):
            return await self._base_container._resolve(abstract)

        return await super()._resolve(abstract)
