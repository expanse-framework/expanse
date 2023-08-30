from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Self


if TYPE_CHECKING:
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

    @classmethod
    def get(cls, path: str, endpoint: Endpoint, *, name: str | None = None) -> Self:
        return cls(path, endpoint, methods=["GET"], name=name)

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
