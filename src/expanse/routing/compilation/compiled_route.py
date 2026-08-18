from typing import Any

from expanse.http.request import Request
from expanse.routing.compilation.argument_binder import ArgumentBinder


class CompiledRoute:
    def __init__(self, argument_binders: list[ArgumentBinder]) -> None:
        self._argument_binders: list[ArgumentBinder] = argument_binders

    async def bind(self, request: Request) -> dict[str, Any]:
        """
        Binds the request to the route's parameters using the precomputed
        argument binders.
        """
        bound_arguments: dict[str, Any] = {}

        for binder in self._argument_binders:
            if binder.is_async:
                bound_arguments[binder.name] = await binder.resolve(request)
            else:
                bound_arguments[binder.name] = binder.resolve(request)

        return bound_arguments
