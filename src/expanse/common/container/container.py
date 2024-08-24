# ruff: noqa: I002
import builtins
import collections
import inspect
import logging
import types
import typing

from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections.abc import Callable
from inspect import Parameter
from typing import Any
from typing import Self
from typing import TypeVar
from typing import _AnnotatedAlias  # type: ignore[attr-defined]
from typing import get_args

from expanse.common.support._utils import eval_type_lenient


T = TypeVar("T")

_builtins = {d for d in dir(builtins) if isinstance(getattr(builtins, d), type)}
_typing_builtins = {Any}
_typing_builtins_strings = {str(t) for t in _typing_builtins}
_EMPTY = object()

logger = logging.getLogger(__name__)

_Callback = Callable[..., Any]


class UnboundAbstractError(Exception): ...


class Container(ABC):
    def __init__(self) -> None:
        self._bindings: dict[str | type, Any] = {}
        self._resolved: dict[str | type, bool] = {}
        self._instances: dict[str | type, Any] = {}
        self._aliases: dict[str, str | type] = {}

        self._scoped_bindings: dict[str | type, Any] = {}

        self._after_resolving_callbacks: dict[str | type, list[_Callback]] = (
            defaultdict(list)
        )

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
            concrete = self._concrete_closure(abstract, concrete)

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

    def alias(self, abstract: str | type, alias: str) -> None:
        self._aliases[alias] = abstract

    def bound(self, abstract: str | type) -> bool:
        return abstract in self._bindings or abstract in self._instances

    def has(self, abstract: str | type) -> bool:
        return self.bound(abstract)

    @abstractmethod
    def create_scoped_container(self) -> Self: ...

    def has_scoped_bindings(self) -> bool:
        return bool(self._scoped_bindings)

    def resolved(self, abstract: str | type) -> bool:
        abstract = self._get_alias(abstract)

        return abstract in self._resolved

    def after_resolving(self, abstract: str | type, callback: _Callback) -> None:
        abstract = self._get_alias(abstract)

        actual_abstract: str | type = abstract
        if isinstance(abstract, _AnnotatedAlias):
            actual_abstract, *_ = get_args(abstract)

        if abstract in self._bindings:
            self._after_resolving_callbacks[abstract].append(callback)
        elif actual_abstract in self._bindings:
            self._after_resolving_callbacks[actual_abstract].append(callback)
        else:
            self._after_resolving_callbacks[abstract].append(callback)

    @abstractmethod
    def _concrete_closure(
        self, abstract: str | type, concrete: Any
    ) -> Callable[[Self], Any]: ...

    def _is_buildable(self, abstract: str | type, concrete: Any) -> bool:
        return abstract == concrete or isinstance(
            concrete, types.FunctionType | types.MethodType
        )

    def _is_cached(self, abstract: str | type) -> bool:
        return abstract in self._instances or self._bindings.get(abstract, {}).get(
            "cached", False
        )

    def _mark_as_resolved(self, abstract: str | type) -> None:
        self._resolved[abstract] = True

    def _get_class(
        self, parameter: Parameter, *, _globals: dict[str, Any] | None = None
    ) -> type | None:
        type_ = parameter.annotation

        if type_ is Parameter.empty:
            return None

        # TODO: handle optionals

        if isinstance(type_, types.UnionType):
            # TODO: check that the union type is a single type optional
            # Get the first type of the type union
            type_ = get_args(type_)[0]

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

                if type_ in _typing_builtins_strings:
                    return True

                return False

        module = inspect.getmodule(type_)
        if module == builtins:
            return True

        if type_ in _typing_builtins:
            return True

        if (
            module == typing or module == collections.abc
        ) and type_.__name__ == "Callable":
            return True

        return False

    def _get_alias(self, abstract: str | type) -> str | type:
        if not isinstance(abstract, str):
            return abstract

        return self._aliases.get(abstract, abstract)

    def _is_lambda(self, callable: _Callback) -> bool:
        return (
            isinstance(callable, types.FunctionType) and callable.__name__ == "<lambda>"
        )
