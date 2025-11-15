from __future__ import annotations

from typing import TYPE_CHECKING

from expanse.schematic.support.extensions.operations.extension import OperationExtension


if TYPE_CHECKING:
    from expanse.schematic.openapi.operation import Operation
    from expanse.schematic.support.route_info import RouteInfo


class EssentialsExtension(OperationExtension):
    def handle(self, operation: Operation, route_info: RouteInfo) -> None:
        # TODO: handle tags

        operation.method = route_info.route.methods[0].lower()
        operation.path = route_info.route.path
        operation.set_operation_id(self._get_operation_id(route_info))

    def _get_operation_id(self, route_info: RouteInfo) -> str:
        if route_info.route.name:
            return route_info.route.name

        handler = route_info.route.endpoint
        if not isinstance(handler, tuple):
            return handler.__name__

        return f"{handler[0].__name__}.{handler[1]}"
