from abc import ABC
from abc import abstractmethod

from expanse.schematic.generator_config import GeneratorConfig
from expanse.schematic.inference.inference import Inference
from expanse.schematic.openapi.openapi import OpenAPI
from expanse.schematic.openapi.operation import Operation
from expanse.schematic.support.route_info import RouteInfo


class OperationExtension(ABC):
    def __init__(
        self, openapi: OpenAPI, inference: Inference, config: GeneratorConfig
    ) -> None:
        self._openapi: OpenAPI = openapi
        self._inference: Inference = inference
        self._config: GeneratorConfig = config

    @abstractmethod
    def handle(self, operation: Operation, route_info: RouteInfo) -> None: ...
