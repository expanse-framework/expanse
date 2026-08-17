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
from expanse.support._concurrency import should_run_as_async
from expanse.support._concurrency import sync_to_async
from expanse.support._utils import eval_type_lenient
from expanse.support._utils import string_to_class


T = TypeVar("T")

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_typing_builtins = {Any}
_typing_builtins_strings = {str(t) for t in _typing_builtins}
_EMPTY = object()

logger = logging.getLogger(__name__)

_Callback = Callable[..., None] | Callable[..., Awaitable[None]]

# inspect.signature() re-walks the MRO, unwraps partials/descriptors, and
# rebuilds a Signature object from scratch every time it's called; for
# functions and classes (registered once, at startup) that work never
# changes, so we memoize it across the many scoped containers created over
# the life of the process. Bound methods are obtained fresh per request
# (e.g. `getattr(instance, name)` on a request-scoped instance), so we
# never cache by the bound method's own identity - that would pin the
# instance in memory and never hit anyway. Instead we cache by `__func__`,
# the underlying plain function shared by every instance of the class, and
# strip its leading `self`/`cls` parameter (same approach as Route, which
# does this once at registration time via the class rather than an
# instance).
_signature_cache: dict[Callable[..., Any] | type, inspect.Signature] = {}

# Similarly, `partial(callback, instance)` (e.g. after_resolving callbacks,
# which rebuild that partial on every resolution to bind the freshly
# resolved instance) produces a fresh, uncacheable-by-identity object each
# time even though its resulting signature never changes: it only depends
# on which parameter slots `callback` + the pre-supplied args/keywords
# consume, never on the actual bound values.
_partial_signature_cache: dict[
    tuple[Callable[..., Any], int, frozenset[str]], inspect.Signature
] = {}


def _cached_signature(obj: Callable[..., Any] | type) -> inspect.Signature:
    if isinstance(obj, partial):
        func = obj.func
        stable_func: Callable[..., Any] = func
        leading = 0
        if isinstance(func, types.MethodType):
            stable_func = func.__func__
            leading = 1

        key = (stable_func, leading + len(obj.args), frozenset(obj.keywords))

        try:
            return _partial_signature_cache[key]
        except KeyError:
            signature = inspect.signature(obj)
            _partial_signature_cache[key] = signature

            return signature

    if isinstance(obj, types.MethodType):
        func = obj.__func__

        try:
            return _signature_cache[func]
        except KeyError:
            unbound_signature = inspect.signature(func)
            signature = unbound_signature.replace(
                parameters=list(unbound_signature.parameters.values())[1:]
            )
            _signature_cache[func] = signature

            return signature

    try:
        return _signature_cache[obj]
    except KeyError:
        signature = inspect.signature(obj)
        _signature_cache[obj] = signature

        return signature


# The injectable type for a given Parameter only depends on its own
# annotation and the defining callable's __globals__, both fixed once that
# callable is registered. Since _cached_signature() means the same
# Parameter objects are now reused across requests, this is memoized the
# same way, keyed by identity of the __globals__ dict (itself stable for
# the life of the module).
_class_cache: dict[tuple[Parameter, int], type | None] = {}


def _cached_class_for_parameter(
    parameter: Parameter, _globals: dict[str, Any] | None
) -> type | None:
    key = (parameter, id(_globals))

    try:
        return _class_cache[key]
    except KeyError:
        result = _class_for_parameter(parameter, _globals)
        _class_cache[key] = result

        return result


def _class_for_parameter(
    parameter: Parameter, _globals: dict[str, Any] | None
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

        if not _is_builtin_type(actual_type, _globals):
            return type_

    if isinstance(type_, TypeVar):
        # Unbound type variables cannot be resolved; treat as primitive
        # so the parameter's default value (if any) is used.
        return None

    type_ = get_origin(type_) or type_

    if _is_builtin_type(type_, _globals):
        return None

    return type_


def _is_builtin_type(type_: Any, _globals: dict[str, Any] | None) -> bool:
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

        # Built lazily, on first actual use in _resolve(). ScopedContainer
        # overrides _resolve() and never acquires this lock at all, so this
        # keeps every per-request ScopedContainer from constructing (and
        # immediately discarding) an AsyncRLock it can never use.
        self._lock: AsyncRLock | None = None

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

                # For parameterized generics (e.g. MyGeneric[int]), concrete.__init__
                # would resolve to _GenericAlias.__init__; introspect the origin instead.
                concrete = get_origin(concrete) or concrete

                function = concrete.__init__  # type: ignore[misc]

                if isinstance(function, types.WrapperDescriptorType):
                    # If the class does not define an __init__ method
                    # call it directly.
                    return concrete(*args), None

                is_class = True

        if is_class:
            # Use the class signature (which excludes `self`) so positional
            # metadata isn't consumed by `self`. Pass `__init__` as the callable
            # so __globals__ remains available for forward-reference resolution.
            (
                positional,
                keywords,
            ) = await self._resolve_signature(
                _cached_signature(concrete), args, {}, callable=function
            )
        else:
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

        if inspect.iscoroutinefunction(concrete):
            return await concrete(*positional, **keywords), None

        if not should_run_as_async(concrete):
            return concrete(*positional, **keywords), None

        return await sync_to_async(concrete, *positional, **keywords), None

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

        if inspect.iscoroutinefunction(callable_):
            return await callable_(*positional, **keywords)

        if not should_run_as_async(callable_):
            return callable_(*positional, **keywords)

        return await sync_to_async(callable_, *positional, **keywords)

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
        # Fast path: once a binding is built (the overwhelmingly common case
        # for singletons resolved on every request - Config, Router, and
        # friends), there's nothing left to protect, so skip the lock
        # entirely instead of paying for it on every single lookup. This is
        # safe as a plain double-checked-locking pattern: on a miss here we
        # still fall through to the locked, authoritative check in
        # _do_resolve() below, so a not-yet-built singleton is still only
        # ever built once under concurrent access.
        alias = self._get_alias(abstract)
        if alias in self._instances:
            return self._instances[alias]

        if self._lock is None:
            self._lock = AsyncRLock()

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
            # Fall back to building the bare class directly. For Annotated[X, ...]
            # we must use `actual_abstract` (the unwrapped class), otherwise
            # `_can_build` returns False and `self.get(concrete)` recurses forever.
            concrete = actual_abstract

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
            _cached_signature(callable), args, kwargs, callable=callable
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
            klass = _cached_class_for_parameter(parameter, _globals)

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
                klass = _cached_class_for_parameter(parameter, _globals)

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
                    klass = _cached_class_for_parameter(parameter, _globals)

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
                    klass = _cached_class_for_parameter(parameter, _globals)

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
                klass = _cached_class_for_parameter(parameter, _globals)

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
        scoped = base_container._scoped

        # Most requests don't touch any scoped bindings at all, so skip
        # these copies - built fresh on every request - when there's
        # nothing to copy, rather than allocating an empty dict/list/dict
        # via comprehension every time.

        # Bind scoped bindings from the base container
        if scoped["bindings"]:
            self._bindings.update({k: {**v} for k, v in scoped["bindings"].items()})

        # Setup terminating callbacks
        if scoped["terminating_callbacks"]:
            self._terminating_callbacks = [*scoped["terminating_callbacks"]]

        # Setup resolving callbacks
        if scoped["after_resolving_callbacks"]:
            self._after_resolving_callbacks = {**scoped["after_resolving_callbacks"]}

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
        if not self.bound(actual_abstract):
            return await self._do_resolve(abstract)

        if not self._directly_bound(actual_abstract):
            return await self._base_container._resolve(abstract)

        return await self._do_resolve(abstract)
