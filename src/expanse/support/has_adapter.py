from abc import ABC
from abc import abstractmethod
from typing import Self

from expanse.support.adapter import Adapter
from expanse.support.adapter import AsyncAdapter


class HasAdapter(ABC):
    @classmethod
    @abstractmethod
    def get_adapter(cls) -> Adapter[Self] | AsyncAdapter[Self]: ...
