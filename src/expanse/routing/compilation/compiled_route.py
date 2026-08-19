import inspect
import types

from dataclasses import dataclass
from typing import Any
from typing import get_args
from typing import get_origin

from expanse.core.http.exceptions import HTTPException
from expanse.http.request import Request
from expanse.routing.compilation.argument_binder import ArgumentBinder
from expanse.types.routing import Endpoint


@dataclass(frozen=True, slots=True)
class CompiledRoute:
    handler: Endpoint | tuple[type, str]
    signature: inspect.Signature
    is_async: bool
    argument_binders: list[ArgumentBinder]

    async def bind(self, request: Request) -> tuple[dict[str, Any], list[str]]:
        """
        Binds the request to the route's parameters using the precomputed
        argument binders.
        """
        bound_arguments: dict[str, Any] = {}

        for binder in self.argument_binders:
            if binder.is_async:
                bound_arguments[binder.name] = await binder.resolve(request)
            else:
                bound_arguments[binder.name] = binder.resolve(request)

        return bound_arguments, [
            name for name in self.signature.parameters if name not in bound_arguments
        ]

    def bind_query(self, request: Request, unbound: list[str]) -> dict[str, Any]:
        """
        Binds the query params to the route's parameters.

        This should only be called after dependencies have been resolved.
        """
        bound_arguments: dict[str, Any] = {}

        for name in unbound:
            parameter = self.signature.parameters[name]
            annotation = (
                parameter.annotation
                if parameter.annotation is not inspect.Parameter.empty
                else None
            )
            if name not in request.query_params:
                # If the parameter is not present in the query parameters,
                # and the annotations indicate that it is optional, return None.
                if (
                    annotation is not None
                    and get_origin(annotation) is types.UnionType
                    and types.NoneType in get_args(annotation)
                ):
                    bound_arguments[name] = None
                    continue

                # Otherwise raise an HTTPException.
                raise HTTPException(400, f"Missing required query parameter: {name}")

            # If the parameter is present, return its value from the query parameters, validating it against the annotation if provided.
            if annotation is not None:
                value = request.query_params[name]
                # Find the first non-None type in the Union for validation
                if get_origin(annotation) is types.UnionType:
                    non_none_types = [
                        t for t in get_args(annotation) if t is not types.NoneType
                    ]
                    if non_none_types:
                        annotation = non_none_types[0]

                try:
                    return annotation(value)
                except (ValueError, TypeError):
                    raise HTTPException(
                        400,
                        f"Invalid value for query parameter '{name}': {value}",
                    )

            bound_arguments[name] = request.query_params[name]

        return bound_arguments
