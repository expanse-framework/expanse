from collections.abc import Mapping
from typing import Any

from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.responses.response import Response
from expanse.view.view_factory import ViewFactory


class ViewResponse(Response):
    __slots__ = ("_data", "_view")

    def __init__(
        self,
        view: str,
        *,
        data: Mapping[str, Any] | None = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        content_type: str = "text/html",
        encoding: str = "utf-8",
    ) -> None:
        super().__init__(
            content=None,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            encoding=encoding,
        )

        self._view: str = view
        self._data: Mapping[str, Any] = data or {}

    async def prepare(self, request: Request, container: Container) -> None:
        factory = await container.get(ViewFactory)

        self._content = await factory.render(factory.make(self._view, data=self._data))

        return await super().prepare(request, container)
