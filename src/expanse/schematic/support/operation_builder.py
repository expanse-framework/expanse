from __future__ import annotations

from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.inference.inference import Inference
from expanse.schematic.openapi.openapi import OpenAPI
from expanse.schematic.openapi.operation import Operation
from expanse.schematic.support.extensions.operations.extension import OperationExtension
from expanse.schematic.support.route_info import RouteInfo


class OperationBuilder:
    """
    Builds OpenAPI Operation objects from routes using extensible builders.
    """

    def __init__(self) -> None:
        self._extensions: list[type[OperationExtension]] = []

    def add_extension(self, extension: type[OperationExtension]) -> None:
        self._extensions.append(extension)

    def set_extensions(self, extensions: list[type[OperationExtension]]) -> None:
        self._extensions = extensions

    def build(
        self,
        openapi: OpenAPI,
        route_info: RouteInfo,
        config: GeneratorConfig,
        inference: Inference,
    ) -> Operation:
        operation = Operation("get")

        for extension_class in self._extensions:
            extension: OperationExtension = extension_class(openapi, inference, config)
            extension.handle(operation, route_info)

        return operation
