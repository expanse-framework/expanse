from __future__ import annotations

import traceback

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Self

from expanse.common.configuration.config import Config
from expanse.common.core.application import Application as BaseApplication
from expanse.common.support._utils import string_to_class
from expanse.container.container import Container
from expanse.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.core.application_builder import ApplicationBuilder
from expanse.core.bootstrap.boot_providers import BootProviders
from expanse.core.bootstrap.load_configuration import LoadConfiguration
from expanse.core.bootstrap.load_environment_variables import LoadEnvironmentVariables
from expanse.core.bootstrap.register_providers import RegisterProviders
from expanse.exceptions.handler import ExceptionHandler


if TYPE_CHECKING:
    from collections.abc import Iterable

    from cleo.io.inputs.input import Input

    from expanse.core.bootstrap.bootstrapper import Bootstrapper
    from expanse.support.service_provider import ServiceProvider
    from expanse.types import Environ
    from expanse.types import StartResponse


class Application(BaseApplication, Container):
    _bootstrappers: ClassVar[list[type[Bootstrapper]]] = [
        LoadEnvironmentVariables,
        LoadConfiguration,
        RegisterProviders,
        BootProviders,
    ]

    def __init__(self, base_path: Path | None = None) -> None:
        BaseApplication.__init__(
            self,
            base_path
            or Path(traceback.extract_stack(limit=2)[0].filename).parent.parent,
        )
        Container.__init__(self)

        self._service_providers: list[ServiceProvider] = []
        self._default_bootstrappers: list[type[Bootstrapper]] = (
            self.__class__._bootstrappers.copy()
        )

        self._bind_paths()
        self._register_base_bindings()

    @classmethod
    def configure(cls, base_path: Path | None = None) -> ApplicationBuilder:
        base_path = (
            base_path
            or Path(traceback.extract_stack(limit=2)[0].filename).parent.parent
        )
        builder = (
            ApplicationBuilder(cls(base_path=base_path)).with_kernels().with_commands()
        )

        return builder

    def set_config(self, config: Config) -> None:
        super().set_config(config)
        self.instance(Config, config)

    def boot(self) -> None:
        """
        Boot the application service providers.
        """
        if self.is_booted():
            return

        for service_provider in self._service_providers:
            self._boot_provider(service_provider)

        self._booted = True

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        self._bind_paths()

        return self

    def bootstrap(self) -> Self:
        return self.bootstrap_with(self._default_bootstrappers)

    def bootstrap_with(self, bootstrappers: list[type[Bootstrapper]]) -> Self:
        if self._has_been_bootstrapped:
            return self

        self._register_base_service_providers()

        for bootstrapper_class in bootstrappers:
            bootstrapper: Bootstrapper = self.make(bootstrapper_class)
            bootstrapper.bootstrap(self)

        self.boot()

        self._has_been_bootstrapped = True

        return self

    def register_configured_providers(self) -> None:
        providers = (self.make(Config)).get("app.providers", [])

        for provider_class in providers:
            if isinstance(provider_class, str):
                provider_class = string_to_class(provider_class)

            provider = provider_class(self)

            self.register(provider)

    def register(
        self, provider: ServiceProvider, force: bool = False
    ) -> ServiceProvider:
        self._service_providers.append(provider)

        provider.register()

        if self._has_been_bootstrapped:
            self._boot_provider(provider)

        return provider

    def handle_command(self, input: Input) -> int:
        from expanse.core.console.kernel import Kernel

        kernel = self.make(Kernel)

        return kernel.handle(input)

    def _bind_paths(self) -> None:
        assert self._base_path is not None

        self.instance("path", self._base_path)
        self.instance("path:config", self.config_path)
        self.instance("path:resources", self.resources_path)

    def _boot_provider(self, provider: ServiceProvider) -> None:
        if hasattr(provider, "boot"):
            self.call(provider.boot)

    def _register_base_bindings(self) -> None:
        from expanse.core.http.gateway import Gateway

        self.instance("app", self)
        self.instance(self.__class__, self)
        self.instance(Container, self)
        self._config = Config({})
        self.instance(Config, self._config)
        self.alias(Config, "config")

        self.singleton(Gateway)

        # TODO: make the exception handler configurable
        self.singleton(ExceptionHandlerContract, ExceptionHandler)

    def _register_base_service_providers(self) -> None:
        from expanse.http.http_service_provider import HTTPServiceProvider
        from expanse.routing.routing_service_provider import RoutingServiceProvider

        self.register(HTTPServiceProvider(self))
        self.register(RoutingServiceProvider(self))

    def __call__(
        self, environ: Environ, start_response: StartResponse
    ) -> Iterable[bytes]:
        from expanse.core.http.gateway import Gateway

        self.bootstrap()

        return self.make(Gateway)(environ, start_response)
