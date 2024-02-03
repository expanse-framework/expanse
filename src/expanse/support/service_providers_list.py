from typing import Self

from expanse.support._utils import class_to_name
from expanse.support.service_provider import ServiceProvider


class ServiceProvidersList:
    def __init__(self, providers: list[type[ServiceProvider] | str]) -> None:
        self._providers: list[str] = [class_to_name(provider) for provider in providers]

    def merge(self, providers: list[type[ServiceProvider] | str]) -> Self:
        return self.__class__([*self._providers, *providers])

    def without(self, providers: list[type[ServiceProvider] | str]) -> Self:
        providers = {class_to_name(provider) for provider in providers}

        new_providers = []
        for current_provider in self._providers:
            if current_provider in providers:
                continue

            new_providers.append(current_provider)

        return self.__class__(new_providers)

    def to_list(self) -> list[str]:
        return self._providers.copy()

    @classmethod
    def default(cls) -> Self:
        return cls(
            [
                "expanse.view.view_service_provider.ViewServiceProvider",
            ]
        )
