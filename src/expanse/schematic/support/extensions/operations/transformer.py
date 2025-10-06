from abc import ABC
from abc import abstractmethod

from expanse.schematic.openapi.operation import Operation


class OperationTransformer(ABC):
    @abstractmethod
    def transform(self, operation: Operation) -> None: ...
