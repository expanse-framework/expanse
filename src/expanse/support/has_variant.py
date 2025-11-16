from abc import ABC
from abc import abstractmethod
from typing import Self

from expanse.support.variant import AsyncVariant
from expanse.support.variant import Variant


class HasVariant(ABC):
    @abstractmethod
    def get_variant(self) -> Variant[Self] | AsyncVariant[Self]:
        raise NotImplementedError("Subclasses must implement get_variant method")
