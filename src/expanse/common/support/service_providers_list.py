from abc import ABC
from typing import Generic
from typing import Self
from typing import TypeVar

from expanse.common.support._utils import class_to_name


T = TypeVar("T")


class ServiceProvidersList(Generic[T], ABC):
    def __init__(self, providers: list[type[T] | str]) -> None:
        self._providers: list[str] = [class_to_name(provider) for provider in providers]

    def merge(self, providers: list[type[T] | str]) -> Self:
        return self.__class__([*self._providers, *providers])

    def without(self, providers: list[type[T] | str]) -> Self:
        provider_names: set[str] = {class_to_name(provider) for provider in providers}

        new_providers: list[str | type] = []
        for current_provider in self._providers:
            if current_provider in provider_names:
                continue

            new_providers.append(current_provider)

        return self.__class__(new_providers)

    def to_list(self) -> list[str]:
        return self._providers.copy()

    @classmethod
    def default(cls) -> Self:
        return cls([])
