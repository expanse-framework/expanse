from __future__ import annotations

from typing import TYPE_CHECKING
from typing import override

from expanse.schematic.analyzers.schema_registry import SchemaRegistry
from expanse.schematic.openapi.parameter import Parameter
from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo


class ParametersExtension(OperationExtension):
    """
    Builds operation parameters (path, query, header) from signature analysis.
    """

    @override
    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        # Path parameters
        for param_info in route_info.signature.path_parameters:
            parameter = Parameter(param_info.name, "path")
            parameter.set_required(True)

            schema = SchemaRegistry(self._openapi.components).generate_from_type(
                param_info.annotation
            )
            parameter.set_schema(schema)

            # Add description from docstring
            if param_info.name in route_info.doc_string.parameters:
                param_doc = route_info.doc_string.parameters[param_info.name]
                if param_doc.description:
                    parameter.set_description(param_doc.description)

            operation.add_parameter(parameter)

        # Query parameters
        for param_info in route_info.signature.query_parameters:
            if param_info.pydantic_model:
                # Generate parameters from Pydantic model fields
                for (
                    field_name,
                    field_info,
                ) in param_info.pydantic_model.model_fields.items():
                    parameter = Parameter(field_name, "query")
                    parameter.set_required(field_info.is_required())

                    # Generate schema from field type
                    schema = self._schema_registry.generate_from_type(
                        field_info.annotation
                    )
                    parameter.set_schema(schema)

                    # Add description from field
                    if field_info.description:
                        parameter.set_description(field_info.description)

                    operation.add_parameter(parameter)
            else:
                parameter = Parameter(param_info.name, "query")
                parameter.set_required(param_info.is_required)

                # Generate schema from type annotation
                schema = self._schema_registry.generate_from_type(param_info.annotation)
                parameter.set_schema(schema)

                # Add description from docstring
                if param_info.name in route_info.doc_string.parameters:
                    param_doc = route_info.doc_string.parameters[param_info.name]
                    if param_doc.description:
                        parameter.set_description(param_doc.description)

                operation.add_parameter(parameter)
