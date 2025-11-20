from abc import ABC
from abc import abstractmethod
from typing import Self

from expanse.support.adapter import Adapter
from expanse.support.adapter import AsyncAdapter


class HasAdapter(ABC):
    @abstractmethod
    def get_adapter(self) -> Adapter[Self] | AsyncAdapter[Self]: ...
