from __future__ import annotations

import builtins
import inspect
import types

from inspect import Parameter
from typing import TYPE_CHECKING

from expanse.support._utils import string_to_class


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

_builtins = [d for d in dir(builtins) if isinstance(getattr(builtins, d), type)]
_EMPTY = object()


class Container:
    def __init__(self) -> None:
        self._bindings: dict[str, Any] = {}
        self._resolved: dict[str, bool] = {}
        self._instances: dict[str, Any] = {}
        self._scoped_bindings: dict[str, Any] = {}
        self._aliases: dict[str, str] = {}

    def bind(
        self,
        abstract: type | str,
        concrete: Any = None,
        *,
        cached: bool = False,
        scoped: bool = False,
    ) -> None:
        abstract = self._get_abstract_name(abstract)

        if concrete is None:
            concrete = abstract

        if not isinstance(concrete, types.FunctionType):
            original_concrete = concrete

            def _concrete(container: Container) -> Any:
                if abstract == original_concrete:
                    return container.build(original_concrete)

                return container._resolve(original_concrete)

            concrete = _concrete

        if scoped:
            self._scoped_bindings[abstract] = {"concrete": concrete, "cached": cached}
        else:
            self._bindings[abstract] = {
                "concrete": concrete,
                "cached": cached,
                "scoped": scoped,
            }

    def singleton(
        self, abstract: type | str, concrete: Any = None, *, scoped: bool = False
    ) -> None:
        self.bind(abstract, concrete, cached=True, scoped=scoped)

    def scoped(self, abstract: type | str, concrete: Any = None) -> None:
        self.singleton(abstract, concrete, scoped=True)

    def instance(self, abstract: type | str, instance: Any) -> None:
        self._instances[self._get_abstract_name(abstract)] = instance

    def build(self, concrete: type | str) -> Any:
        if isinstance(concrete, types.FunctionType):
            return concrete(self)

        if isinstance(concrete, str):
            concrete = string_to_class(concrete)

        constructor = concrete.__init__  # type: ignore[misc]

        resolved_positional, positional, keywords = self._resolve_callable_dependencies(
            constructor
        )

        return concrete(*resolved_positional, *positional, **keywords)

    def make(self, abstract: str | type) -> Any:
        return self._resolve(abstract)

    def call(self, callable: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        resolved_positional, positional, keywords = self._resolve_callable_dependencies(
            callable
        )

        positional = list(args) + positional[len(args) :]

        return callable(*resolved_positional, *positional, **{**keywords, **kwargs})

    async def call_async(
        self, callable: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        resolved_positional, positional, keywords = self._resolve_callable_dependencies(
            callable
        )

        positional = list(args) + positional[len(args) :]

        return await callable(
            *resolved_positional, *positional, **{**keywords, **kwargs}
        )

    def alias(self, abstract: str | type, alias: str) -> None:
        full_name = self._get_abstract_name(abstract)

        self._aliases[alias] = full_name

    def bound(self, abstract: str | type) -> bool:
        abstract = self._get_abstract_name(abstract)
        return abstract in self._bindings or abstract in self._instances

    def create_scoped_container(self) -> Self:
        container = self.__class__()

        container._bindings = deepcopy(self._bindings)
        container._resolved = deepcopy(self._resolved)
        container._instances = deepcopy(self._instances)
        container._bindings.update(deepcopy(self._scoped_bindings))

        return container

    def has_scoped_bindings(self) -> bool:
        return bool(self._scoped_bindings)

    def _resolve(self, abstract: str | type) -> Any:
        abstract = self._get_abstract_name(abstract)
        abstract = self._get_alias(abstract)

        if abstract in self._bindings:
            concrete = self._bindings[abstract]["concrete"]
        else:
            concrete = abstract

        if abstract in self._instances:
            return self._instances[abstract]

        if self._is_buildable(abstract, concrete):
            try:
                obj = self.build(concrete)
            except Exception:
                raise Exception(f'Unable to build the "{abstract}" dependency')
        else:
            obj = self.make(concrete)

        if self._is_cached(abstract):
            self._instances[abstract] = obj

        self._resolved[abstract] = True

        return obj

    def _is_buildable(self, abstract: str, concrete: Any) -> bool:
        return abstract == concrete or isinstance(concrete, types.FunctionType)

    def _is_cached(self, abstract: str) -> bool:
        return abstract in self._instances or self._bindings.get(abstract, {}).get(
            "cached", False
        )

    def _resolve_callable_dependencies(
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
                result = self._resolve_primitive(parameter)
            else:
                try:
                    result = self._resolve_class(parameter)
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

    def _resolve_primitive(self, parameter: inspect.Parameter) -> Any:
        if parameter.default is not parameter.empty:
            return parameter.default

        return _EMPTY

    def _resolve_class(self, parameter: inspect.Parameter) -> Any:
        klass = self._get_class(parameter)

        assert isinstance(klass, str)

        return self.make(self._get_alias(klass))

    def _get_class(self, parameter: Parameter) -> str | None:
        type_ = parameter.annotation

        if type_ is Parameter.empty:
            return None

        type_ = self._get_abstract_name(type_)

        if type_.removeprefix("builtins.") in _builtins:
            return None

        if isinstance(type_, str) and "." in type_:
            return type_

        return self._get_abstract_name(type_)

    def _get_alias(self, abstract: str) -> str:
        return self._aliases.get(self._get_abstract_name(abstract), abstract)

    def _get_abstract_name(self, abstract: type | str) -> str:
        if isinstance(abstract, str):
            return abstract

        module = abstract.__module__
        name = abstract.__qualname__

        full_name = f"{module}.{name}" if module else name

        return full_name
