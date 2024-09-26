import inspect
import re

from typing import Self

from expanse.core.http.middleware.middleware import Middleware
from expanse.types.routing import Endpoint


class Route:
    def __init__(
        self,
        path: str,
        endpoint: Endpoint,
        *,
        methods: list[str] | None = None,
        name: str | None = None,
    ) -> None:
        self.path: str = path
        self.endpoint: Endpoint = endpoint
        self.methods = methods or ["GET", "HEAD"]
        self.name: str | None = name
        self._param_names: set[str] | None = None
        self._signature: inspect.Signature | None = None

        self._middlewares: list[type[Middleware]] = []

    @classmethod
    def get(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["GET", "HEAD"], name=name)

    @classmethod
    def post(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["POST"], name=name)

    @classmethod
    def put(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["PUT"], name=name)

    @classmethod
    def patch(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["PATCH"], name=name)

    @classmethod
    def delete(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["DELETE"], name=name)

    @classmethod
    def options(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["OPTIONS"], name=name)

    @classmethod
    def head(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["HEAD"], name=name)

    @property
    def param_names(self) -> set[str]:
        if self._param_names is None:
            self._param_names = set(re.findall(r"{([^:]*)(?::.*)?}", self.path))

        return self._param_names

    @property
    def signature(self) -> inspect.Signature:
        if self._signature is None:
            self._signature = inspect.signature(self.endpoint)

        return self._signature

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.path}", {self.endpoint})'

    def get_middleware(self) -> list[type[Middleware]]:
        return self._middlewares

    def middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares.extend(middlewares)

        return self

    def prepend_middleware(self, *middlewares: type[Middleware]) -> Self:
        self._middlewares = list(middlewares) + self._middlewares

        return self
