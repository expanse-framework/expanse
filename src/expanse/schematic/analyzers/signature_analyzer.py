from __future__ import annotations

import inspect

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import get_args
from typing import get_origin
from typing import get_type_hints

from pydantic import BaseModel

from expanse.http.form import Form
from expanse.http.json import JSON
from expanse.http.query import Query
from expanse.http.request import Request
from expanse.http.response import Response


if TYPE_CHECKING:
    from expanse.routing.route import Route


@dataclass
class ParameterInfo:
    """Information about a single parameter in a route handler."""

    name: str
    annotation: Any
    default: Any
    kind: str  # 'path', 'query', 'body', 'header', 'form', 'dependency'
    is_required: bool
    pydantic_model: type[BaseModel] | None = None
    data_source: type[JSON] | type[Query] | type[Form] | None = None


@dataclass
class SignatureInfo:
    """Complete signature information for a route handler."""

    parameters: list[ParameterInfo] = field(default_factory=list)
    return_annotation: Any = None
    path_parameters: list[ParameterInfo] = field(default_factory=list)
    query_parameters: list[ParameterInfo] = field(default_factory=list)
    body_parameter: ParameterInfo | None = None
    form_parameter: ParameterInfo | None = None
    has_request: bool = False
    has_response: bool = False


class SignatureAnalyzer:
    """
    Analyzes function signatures to extract parameter and return type information.
    Handles Pydantic models, path parameters, query parameters, and request bodies.
    """

    def analyze(self, route: Route) -> SignatureInfo:
        signature = route.signature
        info = SignatureInfo()

        # Get the actual function for type hint resolution
        if isinstance(route.endpoint, tuple):
            func = getattr(route.endpoint[0], route.endpoint[1])
        else:
            func = route.endpoint

        # Resolve string annotations to actual types
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except Exception:
            # If we can't resolve type hints, fall back to raw annotations
            type_hints = {}

        # Get return annotation
        if "return" in type_hints:
            info.return_annotation = type_hints["return"]
        else:
            info.return_annotation = signature.return_annotation

        for name, parameter in signature.parameters.items():
            # Use resolved type hint if available, otherwise use raw annotation
            annotation = type_hints.get(name, parameter.annotation)
            param_info = self._analyze_parameter(name, parameter, route, annotation)
            if param_info is None:
                continue

            info.parameters.append(param_info)

            # Categorize the parameter
            if param_info.kind == "path":
                info.path_parameters.append(param_info)
            elif param_info.kind == "query":
                info.query_parameters.append(param_info)
            elif param_info.kind == "body":
                info.body_parameter = param_info
            elif param_info.kind == "form":
                info.form_parameter = param_info
            elif param_info.annotation is Request:
                info.has_request = True
            elif param_info.annotation is Response:
                info.has_response = True

        return info

    def _analyze_parameter(
        self,
        name: str,
        parameter: inspect.Parameter,
        route: Route,
        annotation: Any = None,
    ) -> ParameterInfo | None:
        """
        Analyze a single parameter to determine its type and purpose.

        Args:
            name: Parameter name
            parameter: Parameter object from inspect
            route: The route this parameter belongs to
            annotation: Resolved annotation (optional, defaults to parameter.annotation)

        Returns:
            ParameterInfo with extracted information
        """
        if annotation is None:
            annotation = parameter.annotation
        default = parameter.default
        is_required = default is inspect.Parameter.empty

        # Check if it's a path parameter
        if name in route.param_names:
            return ParameterInfo(
                name=name,
                annotation=annotation,
                default=default,
                kind="path",
                is_required=True,  # Path parameters are always required
            )

        # Check if it's a Form parameter
        if self._is_form_parameter(annotation):
            return ParameterInfo(
                name=name,
                annotation=annotation,
                default=default,
                kind="form",
                is_required=is_required,
                data_source=Form,
            )

        # Check if it's an Annotated Pydantic model (JSON or Query)
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            if len(args) >= 2 and self._is_pydantic_model(args[0]):
                pydantic_model = args[0]
                data_type = args[1]

                # Check if data_type is JSON or Query class
                is_json = False
                is_query = False

                try:
                    is_json = isinstance(data_type, type) and issubclass(
                        data_type, JSON
                    )
                except TypeError:
                    pass

                try:
                    is_query = isinstance(data_type, type) and issubclass(
                        data_type, Query
                    )
                except TypeError:
                    pass

                # Also check if it's an instance
                if not is_json and not is_query:
                    is_json = isinstance(data_type, JSON)
                    is_query = isinstance(data_type, Query)

                if is_json or is_query:
                    kind = "body" if is_json else "query"
                    data_source = (
                        data_type if isinstance(data_type, type) else type(data_type)
                    )
                    return ParameterInfo(
                        name=name,
                        annotation=annotation,
                        default=default,
                        kind=kind,
                        is_required=is_required,
                        pydantic_model=pydantic_model,
                        data_source=data_source,
                    )

        # Check if it's a standalone Pydantic model (assume body)
        if self._is_pydantic_model(annotation):
            return ParameterInfo(
                name=name,
                annotation=annotation,
                default=default,
                kind="body",
                is_required=is_required,
                pydantic_model=annotation,
            )

        return None

    def _is_pydantic_model(self, annotation: Any) -> bool:
        """Check if an annotation is a Pydantic model."""
        try:
            return isinstance(annotation, type) and issubclass(annotation, BaseModel)
        except TypeError:
            return False

    def _is_form_parameter(self, annotation: Any) -> bool:
        """Check if an annotation represents a Form parameter."""
        try:
            return isinstance(annotation, type) and issubclass(annotation, Form)
        except TypeError:
            return False

    def _is_query_parameter(self, annotation: Any) -> bool:
        """Check if an annotation represents a Query parameter."""
        try:
            return isinstance(annotation, type) and issubclass(annotation, Query)
        except TypeError:
            return False
