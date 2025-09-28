import asyncio
import builtins
import collections
import inspect
import logging
import types
import typing

from collections import defaultdict
from collections.abc import Awaitable
from collections.abc import Callable
from functools import partial
from inspect import Parameter
from inspect import isasyncgenfunction
from inspect import isgeneratorfunction
from typing import Annotated
from typing import Any
from typing import Self
from typing import TypedDict
from typing import TypeVar
from typing import get_args
from typing import get_origin
from typing import overload

from expanse.container.exceptions import ContainerException
from expanse.container.exceptions import ResolutionException
from expanse.container.exceptions import UnboundAbstractException
from expanse.support._concurrency import AsyncRLock
from expanse.support._concurrency import run_in_threadpool
from expanse.support._utils import eval_type_lenient
from expanse.support._utils import string_to_class


T = TypeVar("T")

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_typing_builtins = {Any}
_typing_builtins_strings = {str(t) for t in _typing_builtins}
_EMPTY = object()

logger = logging.getLogger(__name__)

_Callback = Callable[..., None] | Callable[..., Awaitable[None]]


class _Scoped(TypedDict):
    bindings: dict[str | type, Any]
    terminating_callbacks: list[_Callback]
    after_resolving_callbacks: dict[str | type, list[_Callback]]
    aliases: dict[str, str | type]


class Container:
    __slots__ = (
        "_after_resolving_callbacks",
        "_aliases",
        "_bindings",
        "_instances",
        "_lock",
        "_resolved",
        "_scoped",
        "_scoped_bindings",
        "_terminating_callbacks",
    )

    def __init__(self) -> None:
        self._bindings: dict[str | type, Any] = {}
        self._resolved: dict[str | type, bool] = {}
        self._instances: dict[str | type, Any] = {}
        self._aliases: dict[str, str | type] = {}

        self._scoped_bindings: dict[str | type, Any] = {}

        self._after_resolving_callbacks: dict[str | type, list[_Callback]] = (
            defaultdict(list)
        )
        self._scoped: _Scoped = {
            "bindings": {},
            "terminating_callbacks": [],
            "after_resolving_callbacks": defaultdict(list),
            "aliases": {},
        }

        self._terminating_callbacks: list[_Callback] = []
        self._lock = AsyncRLock()

    def register(
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
            concrete = self._concrete_closure(abstract, concrete)

        if scoped:
            self._scoped["bindings"][abstract] = {
                "concrete": concrete,
                "cached": cached,
            }
        else:
            self._bindings[abstract] = {"concrete": concrete, "cached": cached}

    def singleton(
        self, abstract: type | str, concrete: Any = None, *, scoped: bool = False
    ) -> None:
        self.register(abstract, concrete, cached=True, scoped=scoped)

    def scoped(self, abstract: type | str, concrete: Any = None) -> None:
        self.singleton(abstract, concrete, scoped=True)

    def instance(self, abstract: type | str, instance: Any) -> None:
        self._instances[abstract] = instance

    def alias(self, abstract: str | type, alias: str) -> None:
        self._aliases[alias] = abstract

    def bound(self, abstract: str | type) -> bool:
        return abstract in self._bindings or abstract in self._instances

    def has(self, abstract: str | type) -> bool:
        return self.bound(abstract)

    async def build(
        self, concrete: type | str, args: tuple | None = None
    ) -> tuple[Any, _Callback | None]:
        if args is None:
            args = ()

        function: Callable[..., Any]
        is_class: bool = False
        if isinstance(concrete, types.FunctionType):
            if concrete.__name__ == "<lambda>":
                return concrete(self, *args), None

            if "_concrete_closure" in concrete.__qualname__:
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
                # What we are trying to build is a class,
                # so we need to resolve the parameters of the __init__ method.
                function = concrete.__init__  # type: ignore[misc]

                if isinstance(function, types.WrapperDescriptorType):
                    # If the class doe not define an __init__ method
                    # call it directly.
                    return concrete(*args), None

                is_class = True

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

        # If we are trying to build a class, we want to instantiate it directly
        # without executing it in a worker thread since it has an impact on performance.
        if is_class:
            return concrete(*positional, **keywords), None

        if not asyncio.iscoroutinefunction(concrete):
            return await run_in_threadpool(concrete, *positional, **keywords), None

        return await concrete(*positional, **keywords), None

    @overload
    async def get(self, abstract: type[T]) -> T: ...

    @overload
    async def get(self, abstract: str) -> Any: ...

    async def get(self, abstract: str | type[T]) -> Any | T:
        return await self._resolve(abstract)

    async def call(
        self,
        callable_: Callable[..., Any] | tuple[type[T], str],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if isinstance(callable_, tuple):
            instance: Any = await self.get(callable_[0])

            callable_ = getattr(instance, callable_[1])

        assert callable(callable_)

        (
            positional,
            keywords,
        ) = await self._resolve_callable_dependencies(callable_, *args, **kwargs)

        if asyncio.iscoroutinefunction(callable_):
            return await callable_(*positional, **keywords)

        return await run_in_threadpool(callable_, *positional, **keywords)

    def has_scoped_bindings(self) -> bool:
        return bool(self._scoped["bindings"])

    def resolved(self, abstract: str | type) -> bool:
        abstract = self._get_alias(abstract)

        return abstract in self._resolved

    def after_resolving(self, abstract: str | type, callback: _Callback) -> None:
        abstract = self._get_alias(abstract)

        actual_abstract: str | type = abstract
        origin = get_origin(abstract)
        if origin is Annotated:
            actual_abstract, *_ = get_args(abstract)

        if self._is_scoped(abstract):
            self._scoped["after_resolving_callbacks"][abstract].append(callback)
        elif self._is_scoped(actual_abstract):
            self._scoped["after_resolving_callbacks"][actual_abstract].append(callback)
        elif abstract in self._bindings:
            self._after_resolving_callbacks[abstract].append(callback)
        elif actual_abstract in self._bindings:
            self._after_resolving_callbacks[actual_abstract].append(callback)
        else:
            self._after_resolving_callbacks[abstract].append(callback)

    def terminating(self, callback: _Callback, scoped: bool = False) -> None:
        if scoped:
            self._scoped["terminating_callbacks"].append(callback)
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
        if not self._is_scoped(abstract) and self.resolved(abstract):
            await self.call(partial(callback, await self.get(abstract)))

        self.after_resolving(abstract, callback)

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
        async with self._lock:
            return await self._do_resolve(abstract)

    @overload
    async def _do_resolve(self, abstract: type[T]) -> T: ...

    @overload
    async def _do_resolve(self, abstract: str) -> Any: ...

    async def _do_resolve(self, abstract: str | type[T]) -> Any | T:
        abstract = self._get_alias(abstract)

        if abstract in self._instances:
            return self._instances[abstract]

        metadata: tuple = ()
        actual_abstract: str | type = abstract
        origin = get_origin(abstract)
        if origin is Annotated:
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
        if self._can_build(actual_abstract, concrete):
            try:
                obj, terminating_callback = await self.build(concrete, metadata)
            except Exception as e:
                raise ContainerException(
                    f'Unable to build the "{abstract}" dependency'
                ) from e
        else:
            obj = await self.get(concrete)

        if self._is_cached(actual_abstract):
            self._instances[abstract] = obj

        self._mark_as_resolved(actual_abstract)
        if terminating_callback is not None:
            self.terminating(
                terminating_callback, scoped=self._is_scoped(actual_abstract)
            )

        await self._execute_after_resolving_callbacks(abstract, obj)

        return obj

    async def _resolve_callable_dependencies(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[list[Any], dict[str, Any]]:
        return await self._resolve_signature(
            inspect.signature(callable), args, kwargs, callable=callable
        )

    async def _resolve_signature(
        self,
        signature: inspect.Signature,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        callable: Callable[..., Any] | None = None,
    ) -> tuple[list[Any], dict[str, Any]]:
        args = args or ()
        kwargs = kwargs or {}
        positional: list[Any] = []
        keywords: dict[str, Any] = {}
        arguments = list(args)
        _globals = (
            getattr(callable, "__globals__", None) if callable is not None else None
        )

        for parameter in signature.parameters.values():
            klass = self._get_class(parameter, _globals=_globals)

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
                        f"(type: {klass.__module__ + '.' + klass.__qualname__}) "
                        f"{f'in {callable.__qualname__}' if callable else ''}"
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
        result: Any | list[Any]
        match parameter.kind:
            case parameter.POSITIONAL_ONLY:
                klass = self._get_class(parameter, _globals=_globals)

                assert klass is not None

                if klass is Container:
                    # Shortcut for the container itself
                    # We previously registered the container as an instance,
                    # but it causes performance issues when creating scoped containers
                    result = self
                elif self.has(self._get_alias(klass)):
                    result = await self.get(self._get_alias(klass))
                else:
                    try:
                        result = await self.get(self._get_alias(klass))
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

                    if klass is Container:
                        # Shortcut for the container itself
                        # We previously registered the container as an instance,
                        # but it causes performance issues when creating scoped containers
                        result = self
                    elif self.has(self._get_alias(klass)):
                        result = await self.get(self._get_alias(klass))
                    else:
                        try:
                            result = await self.get(self._get_alias(klass))
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

                    if klass is Container:
                        # Shortcut for the container itself
                        # We previously registered the container as an instance,
                        # but it causes performance issues when creating scoped containers
                        result = self
                    else:
                        result = await self.get(self._get_alias(klass))

                    keywords[parameter.name] = result
                return

            case parameter.VAR_POSITIONAL:
                klass = self._get_class(parameter, _globals=_globals)

                assert klass is not None

                if klass is Container:
                    # Shortcut for the container itself
                    # We previously registered the container as an instance,
                    # but it causes performance issues when creating scoped containers
                    result = self
                else:
                    result = await self.get(self._get_alias(klass))

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
        callbacks: list[_Callback] = []
        abstract = self._get_alias(abstract)

        actual_abstract: str | type = abstract
        origin = get_origin(abstract)
        if origin is Annotated:
            actual_abstract, *_ = get_args(abstract)

        if abstract in self._after_resolving_callbacks:
            callbacks += self._after_resolving_callbacks[abstract]
        elif actual_abstract in self._after_resolving_callbacks:
            callbacks += self._after_resolving_callbacks[actual_abstract]

        for callback in callbacks:
            await self.call(partial(callback, instance))

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        await self.terminate()

    def _can_build(self, abstract: str | type, concrete: Any) -> bool:
        return abstract == concrete or isinstance(
            concrete, types.FunctionType | types.MethodType
        )

    def _is_cached(self, abstract: str | type) -> bool:
        return abstract in self._instances or self._bindings.get(abstract, {}).get(
            "cached", False
        )

    def _is_scoped(self, abstract: str | type) -> bool:
        return self._get_alias(abstract) in self._scoped["bindings"]

    def _mark_as_resolved(self, abstract: str | type) -> None:
        self._resolved[abstract] = True

    def _get_class(
        self, parameter: inspect.Parameter, *, _globals: dict[str, Any] | None = None
    ) -> type | None:
        type_ = parameter.annotation

        if type_ is Parameter.empty:
            return None

        # TODO: handle optionals

        if isinstance(type_, types.UnionType):
            # TODO: check that the union type is a single type optional
            # Get the first type of the type union
            type_ = get_args(type_)[0]

        origin = get_origin(type_)
        if origin is Annotated:
            actual_type, *_ = get_args(type_)

            if not self._is_builtin(actual_type, _globals=_globals):
                return type_

        if self._is_builtin(type_, _globals=_globals):
            return None

        return type_

    def _is_builtin(
        self, type_: type, *, _globals: dict[str, Any] | None = None
    ) -> bool:
        if isinstance(type_, str):
            type_ = eval_type_lenient(type_, _globals, _globals)

            if isinstance(type_, typing.ForwardRef):
                type_ = type_.__forward_arg__

                return type_ in _typing_builtins_strings

        module = inspect.getmodule(type_)
        if module == builtins:
            return True

        if type_ in _typing_builtins:
            return True

        return module == typing or (
            module == collections.abc and type_.__name__ == "Callable"
        )

    def _get_alias(self, abstract: str | type) -> str | type:
        if not isinstance(abstract, str):
            return abstract

        return self._aliases.get(abstract, abstract)

    def _is_lambda(self, callable: _Callback) -> bool:
        return (
            isinstance(callable, types.FunctionType) and callable.__name__ == "<lambda>"
        )


class ScopedContainer(Container):
    __slots__ = ("_base_container",)

    def __init__(self, base_container: Container):
        super().__init__()

        self._base_container = base_container

        # Bind scoped bindings from the base container
        self._bindings.update(
            {k: {**v} for k, v in self._base_container._scoped["bindings"].items()}
        )

        # Setup terminating callbacks
        self._terminating_callbacks = [
            *self._base_container._scoped["terminating_callbacks"]
        ]

        # Setup resolving callbacks
        self._after_resolving_callbacks = {
            **self._base_container._scoped["after_resolving_callbacks"]
        }

    def bound(self, abstract: str | type) -> bool:
        return self._base_container.bound(abstract) or super().bound(abstract)

    def _directly_bound(self, abstract: str | type) -> bool:
        return super().bound(abstract)

    async def _resolve(self, abstract: str | type[T]) -> Any | T:
        actual_abstract: str | type[T] = abstract
        origin = get_origin(abstract)
        if origin is Annotated:
            actual_abstract, *_ = get_args(abstract)

        # If the abstract is neither bound in the container nor in its base container,
        # we will resolve it from the scoped container.
        if not self.bound(abstract):
            return await self._do_resolve(abstract)

        if not self._directly_bound(actual_abstract):
            return await self._base_container._resolve(abstract)

        return await self._do_resolve(abstract)
