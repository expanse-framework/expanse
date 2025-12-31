import inspect
import re
import types

from typing import Self

from expanse.core.http.middleware.middleware import Middleware
from expanse.types.routing import Endpoint


class Route:
    def __init__(
        self,
        method: str | list[str],
        path: str,
        endpoint: Endpoint | tuple[type, str],
        *,
        methods: list[str] | None = None,
        name: str | None = None,
    ) -> None:
        self.path: str = path

        self.signature: inspect.Signature
        if (
            isinstance(endpoint, types.FunctionType)
            and "." in endpoint.__qualname__
            and not inspect.ismethod(endpoint)
            and "<locals>" not in endpoint.__qualname__
        ):
            # We have an instance method, so we will retrieve the corresponding class,
            # resolve it and call the method.
            class_name, func_name = endpoint.__qualname__.rsplit(".", maxsplit=1)
            class_: type = endpoint.__globals__[class_name]

            endpoint = (class_, func_name)

        if isinstance(endpoint, tuple):
            handler_method = getattr(endpoint[0], endpoint[1])
            self.is_async = inspect.iscoroutinefunction(handler_method)

            signature = inspect.signature(handler_method)
            self.signature = inspect.Signature(
                list(signature.parameters.values())[1:],
                return_annotation=signature.return_annotation,
            )

        else:
            self.is_async = inspect.iscoroutinefunction(endpoint)
            self.signature = inspect.signature(endpoint)

        self.endpoint: Endpoint | tuple[type, str] = endpoint
        if isinstance(method, str):
            method = [method]

        self.methods = [m.upper() for m in method]
        self.name: str | None = name
        self._param_names: set[str] | None = None

        self._middlewares: list[type[Middleware] | str] = []

    @classmethod
    def get(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("GET", path, endpoint, name=name)

    @classmethod
    def post(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("POST", path, endpoint, name=name)

    @classmethod
    def put(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("PUT", path, endpoint, name=name)

    @classmethod
    def patch(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("PATCH", path, endpoint, name=name)

    @classmethod
    def delete(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("DELETE", path, endpoint, name=name)

    @classmethod
    def options(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("OPTIONS", path, endpoint, name=name)

    @classmethod
    def head(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls("HEAD", path, endpoint, name=name)

    @property
    def param_names(self) -> set[str]:
        if self._param_names is None:
            self._param_names = set(re.findall(r"{\*?([^:]*)(?::.*)?}", self.path))

        return self._param_names

    @property
    def formatted_endpoint(self) -> str:
        if isinstance(self.endpoint, tuple):
            return f"{self.endpoint[0].__qualname__}.{self.endpoint[1]}"

        return self.endpoint.__qualname__

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.path}", {self.endpoint})'

    def get_middleware(self) -> list[type[Middleware] | str]:
        return self._middlewares

    def middleware(self, *middlewares: type[Middleware] | str) -> Self:
        self._middlewares.extend(middlewares)

        return self

    def prepend_middleware(self, *middlewares: type[Middleware] | str) -> Self:
        self._middlewares = list(middlewares) + self._middlewares

        return self
