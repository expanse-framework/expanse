from __future__ import annotations

import inspect
import re

from enum import Enum
from typing import TYPE_CHECKING
from typing import Self

from baize.routing import Route as BaseRoute


if TYPE_CHECKING:
    from expanse.types.routing import Endpoint


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class Route(BaseRoute):
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
