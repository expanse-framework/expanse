import inspect
import types

from functools import partial
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin

import msgspec

from expanse.http.form import Form
from expanse.http.json import JSON
from expanse.http.query import Query
from expanse.http.request import Request
from expanse.routing.compilation.argument_binder import ArgumentBinder
from expanse.routing.compilation.compiled_route import CompiledRoute
from expanse.routing.route import Route
from expanse.support._model_types import is_msgspec_struct
from expanse.support._model_types import is_pydantic_model
from expanse.types.routing import Endpoint


class RouteCompiler:
    def compile(self, route: Route) -> CompiledRoute:
        handler, signature, is_async = self._compile_handler(route)

        return CompiledRoute(
            handler,
            signature,
            is_async,
            self._compile_argument_binders(route, signature),
        )

    def _compile_handler(
        self, route: Route
    ) -> tuple[Endpoint | tuple[type, str], inspect.Signature, bool]:
        endpoint = route.endpoint

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
            is_async = inspect.iscoroutinefunction(handler_method)

            signature = inspect.signature(handler_method)
            signature = inspect.Signature(
                list(signature.parameters.values())[1:],
                return_annotation=signature.return_annotation,
            )

        else:
            is_async = inspect.iscoroutinefunction(endpoint)
            signature = inspect.signature(endpoint)

        return endpoint, signature, is_async

    def _compile_argument_binders(
        self, route: Route, signature: inspect.Signature
    ) -> list[ArgumentBinder]:
        """
        Precomputes, once per route, how each parameter that needs a value
        pulled from the request (path params, form/JSON/query-validated models)
        should be bound. Parameters not covered here are left for DI to
        resolve.
        """
        binders: list[ArgumentBinder] = []

        for name, parameter in signature.parameters.items():
            if name in route.param_names:
                binders.append(
                    ArgumentBinder(
                        name, False, partial(self._bind_path_param, name=name)
                    )
                )
                continue

            annotation = parameter.annotation

            if isinstance(annotation, type) and issubclass(annotation, Form):
                binders.append(
                    ArgumentBinder(
                        name, True, partial(self._bind_form, annotation=annotation)
                    )
                )
                continue

            if get_origin(annotation) is not Annotated:
                continue

            validation_model, data_type = get_args(annotation)

            if not (
                is_pydantic_model(validation_model)
                or is_msgspec_struct(validation_model)
            ):
                continue

            is_pydantic = is_pydantic_model(validation_model)

            if isinstance(data_type, JSON) or issubclass(data_type, JSON):  # type: ignore[arg-type, misc]
                binders.append(
                    ArgumentBinder(
                        name,
                        True,
                        partial(
                            self._bind_json,
                            model=validation_model,
                            is_pydantic=is_pydantic,
                        ),
                    )
                )
            elif isinstance(data_type, Query) or issubclass(data_type, Query):  # type: ignore[arg-type, misc]
                binders.append(
                    ArgumentBinder(
                        name,
                        False,
                        partial(
                            self._bind_query,
                            model=validation_model,
                            is_pydantic=is_pydantic,
                        ),
                    )
                )

        return binders

    def _bind_path_param(self, request: Request, *, name: str) -> Any:
        return request.path_params[name]

    async def _bind_form(self, request: Request, *, annotation: type[Form]) -> Form:
        return annotation(await request.form)

    async def _bind_json(
        self, request: Request, *, model: Any, is_pydantic: bool
    ) -> Any:
        raw = await request.json

        if is_pydantic:
            return model.model_validate(raw)

        return msgspec.convert(raw, type=model, strict=False)

    def _bind_query(self, request: Request, *, model: Any, is_pydantic: bool) -> Any:
        if is_pydantic:
            return model.model_validate(request.query_params)

        return msgspec.convert(request.query_params, type=model, strict=False)
