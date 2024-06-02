from typing import Self

from expanse.asynchronous.support.service_provider import ServiceProvider
from expanse.common.support.service_providers_list import (
    ServiceProvidersList as BaseServiceProvidersList,
)


class ServiceProvidersList(BaseServiceProvidersList[ServiceProvider]):
    @classmethod
    def default(cls) -> Self:
        return cls(
            [
                "expanse.core.support.providers.core_service_provider.CoreServiceProvider",
                "expanse.core.console.providers.command_service_provider.CommandServiceProvider",
                "expanse.database.database_service_provider.DatabaseServiceProvider",
                "expanse.view.view_service_provider.ViewServiceProvider",
                "expanse.static.static_service_provider.StaticServiceProvider",
            ]
        )
