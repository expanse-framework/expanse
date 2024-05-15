from __future__ import annotations

import traceback

from collections.abc import Awaitable
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Self

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.contracts.debug.exception_handler import (
    ExceptionHandler as ExceptionHandlerContract,
)
from expanse.asynchronous.core.application_builder import ApplicationBuilder
from expanse.asynchronous.core.bootstrap.boot_providers import BootProviders
from expanse.asynchronous.core.bootstrap.load_configuration import LoadConfiguration
from expanse.asynchronous.core.bootstrap.load_environment_variables import (
    LoadEnvironmentVariables,
)
from expanse.asynchronous.core.bootstrap.register_providers import RegisterProviders
from expanse.asynchronous.exceptions.handler import ExceptionHandler
from expanse.common.configuration.config import Config
from expanse.common.core.application import Application as BaseApplication
from expanse.common.support._utils import string_to_class


if TYPE_CHECKING:
    from cleo.io.inputs.input import Input

    from expanse.asynchronous.core.bootstrap.bootstrapper import Bootstrapper
    from expanse.asynchronous.support.service_provider import ServiceProvider
    from expanse.asynchronous.types import Receive
    from expanse.asynchronous.types import Scope
    from expanse.asynchronous.types import Send


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
        self._default_bootstrappers: list[
            type[Bootstrapper]
        ] = self.__class__._bootstrappers.copy()
        self._bootstrapping_callbacks: list[Callable[[Self], Awaitable[None]]] = []

        self._bind_paths()
        self._register_base_bindings()

    @classmethod
    def configure(cls, base_path: Path | None = None) -> ApplicationBuilder:
        base_path = (
            base_path
            or Path(traceback.extract_stack(limit=2)[0].filename).parent.parent
        )

        return ApplicationBuilder(base_path).with_kernels().with_commands()

    def set_config(self, config: Config) -> None:
        super().set_config(config)
        self.instance(Config, config)

    async def boot(self) -> None:
        """
        Boot the application service providers.
        """
        if self.is_booted():
            return

        for service_provider in self._service_providers:
            await self._boot_provider(service_provider)

        self._booted = True

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        self._bind_paths()

        return self

    async def bootstrap(self) -> Self:
        return await self.bootstrap_with(self._default_bootstrappers)

    async def bootstrap_with(self, bootstrappers: list[type[Bootstrapper]]) -> Self:
        if self._has_been_bootstrapped:
            return self

        await self._register_base_service_providers()

        for bootstrapper_class in bootstrappers:
            bootstrapper: Bootstrapper = await self.make(bootstrapper_class)
            await bootstrapper.bootstrap(self)

        for callback in self._bootstrapping_callbacks:
            await callback(self)

        await self.boot()

        self._has_been_bootstrapped = True

        return self

    def bootstrapping(self, *callback: Callable[[Self], Awaitable[None]]) -> Self:
        self._bootstrapping_callbacks.extend(callback)

        return self

    async def register_configured_providers(self) -> None:
        providers = (await self.make(Config)).get("app.providers", [])

        for provider_class in providers:
            if isinstance(provider_class, str):
                provider_class = string_to_class(provider_class)

            provider = provider_class(self)

            await self.register(provider)

    async def register(
        self, provider: ServiceProvider, force: bool = False
    ) -> ServiceProvider:
        self._service_providers.append(provider)

        await provider.register()

        return provider

    async def handle_command(self, input: Input) -> int:
        from expanse.asynchronous.core.console.kernel import Kernel

        kernel = await self.make(Kernel)

        return await kernel.handle(input)

    def _bind_paths(self) -> None:
        assert self._base_path is not None

        self.instance("path", self._base_path)
        self.instance("path:config", self.config_path)
        self.instance("path:resources", self.resources_path)

    async def _boot_provider(self, provider: ServiceProvider) -> None:
        if hasattr(provider, "boot"):
            await self.call(provider.boot)

    def _register_base_bindings(self) -> None:
        from expanse.asynchronous.core.http.gateway import Gateway

        self.instance("app", self)
        self.instance(self.__class__, self)
        self.instance(Container, self)
        self._config = Config({})
        self.instance(Config, self._config)
        self.alias(Config, "config")

        self.singleton(Gateway)

        # TODO: make the exception handler configurable
        self.singleton(ExceptionHandlerContract, ExceptionHandler)

    async def _register_base_service_providers(self) -> None:
        from expanse.asynchronous.http.http_service_provider import HTTPServiceProvider
        from expanse.asynchronous.routing.routing_service_provider import (
            RoutingServiceProvider,
        )

        await self.register(HTTPServiceProvider(self))
        await self.register(RoutingServiceProvider(self))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await self.bootstrap()
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await self.terminate()
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        from expanse.asynchronous.core.http.gateway import Gateway

        gateway = await self.make(Gateway)

        await gateway(scope, receive, send)
