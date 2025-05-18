from __future__ import annotations

import traceback

from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Self

from expanse.configuration.config import Config
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
from expanse.support._utils import string_to_class


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from cleo.io.inputs.input import Input

    from expanse.core.bootstrap.bootstrapper import Bootstrapper
    from expanse.support.service_provider import ServiceProvider
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Application:
    _bootstrappers: ClassVar[list[type[Bootstrapper]]] = [
        LoadEnvironmentVariables,
        LoadConfiguration,
        RegisterProviders,
        BootProviders,
    ]

    def __init__(
        self, base_path: Path | None = None, container: Container | None = None
    ) -> None:
        if container is None:
            container = Container()

        self._container = container

        self._base_path: Path = (
            base_path
            or Path(traceback.extract_stack(limit=2)[0].filename).parent.parent
        )
        self._config_path: Path | None = None
        self._environment_path: Path | None = None

        self._booted: bool = False
        self._has_been_bootstrapped: bool = False
        self._config: Config
        self._service_providers: list[ServiceProvider] = []
        self._default_bootstrappers: list[type[Bootstrapper]] = (
            self.__class__._bootstrappers.copy()
        )
        self._bootstrapping_callbacks: list[Callable[[Container], Awaitable[None]]] = []

        self._bind_paths()
        self._register_base_bindings()

    @property
    def name(self) -> str:
        return self._config.get("app.name", "Expanse")

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def config_path(self) -> Path:
        return self._config_path or self._base_path.joinpath("config")

    @property
    def environment_path(self) -> Path:
        return self._environment_path or self._base_path

    @property
    def environment(self) -> str:
        return self._config.get("app.env", "production")

    def path(self, path: str | Path, relative: bool = False) -> Path:
        path = self._base_path.joinpath("app").joinpath(path)

        if relative:
            path = path.relative_to(self._base_path)

        return path

    def named_path(self, name: str) -> Path:
        path_key = f"paths.{name}"
        if path_key not in self._config:
            raise ValueError(f"Named path {name} is not configured.")

        path: Path = self._config[path_key]

        return self._base_path.joinpath(path)

    @property
    def environment_file(self) -> str:
        return ".env"

    @property
    def config(self) -> Config:
        return self._config

    def is_booted(self) -> bool:
        return self._booted

    def has_been_bootstrapped(self) -> bool:
        return self._has_been_bootstrapped

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        self._bind_paths()

        return self

    @property
    def container(self) -> Container:
        return self._container

    @classmethod
    def configure(cls, base_path: Path | None = None) -> ApplicationBuilder:
        base_path = (
            base_path
            or Path(traceback.extract_stack(limit=2)[0].filename).parent.parent
        )

        return ApplicationBuilder(base_path).with_portals().with_commands()

    def set_config(self, config: Config) -> None:
        self._config = config
        self._container.instance(Config, config)

    async def boot(self) -> None:
        """
        Boot the application service providers.
        """
        if self.is_booted():
            return

        for service_provider in self._service_providers:
            await self._boot_provider(service_provider)

        self._booted = True

    async def bootstrap(self) -> Self:
        return await self.bootstrap_with(self._default_bootstrappers)

    async def bootstrap_with(self, bootstrappers: list[type[Bootstrapper]]) -> Self:
        if self._has_been_bootstrapped:
            return self

        await self._register_base_service_providers()

        for bootstrapper_class in bootstrappers:
            bootstrapper: Bootstrapper = await self._container.get(bootstrapper_class)
            await bootstrapper.bootstrap(self)

        for callback in self._bootstrapping_callbacks:
            await callback(self._container)

        self._has_been_bootstrapped = True

        return self

    def bootstrapping(self, *callback: Callable[[Container], Awaitable[None]]) -> Self:
        self._bootstrapping_callbacks.extend(callback)

        return self

    async def register_configured_providers(self) -> None:
        providers = (await self._container.get(Config)).get("app.providers", [])

        for provider_class in providers:
            if isinstance(provider_class, str):
                provider_class = string_to_class(provider_class)

            provider = provider_class(self._container)

            await self.register(provider)

    async def register(
        self, provider: ServiceProvider, force: bool = False
    ) -> ServiceProvider:
        self._service_providers.append(provider)

        await provider.register()

        return provider

    async def handle_command(self, input: Input) -> int:
        from expanse.core.console.portal import Portal

        portal = await self._container.get(Portal)

        return await portal.handle(input)

    def _bind_paths(self) -> None:
        assert self._base_path is not None

        self._container.instance("path", self._base_path)
        self._container.instance("path:config", self.config_path)

    async def _boot_provider(self, provider: ServiceProvider) -> None:
        if hasattr(provider, "boot"):
            await self._container.call(provider.boot)

    def _register_base_bindings(self) -> None:
        from expanse.core.http.portal import Portal

        self._container.instance(self.__class__, self)
        self._container.alias(self.__class__, "app")
        self._container.instance(Container, self._container)
        self._config = Config({})
        self._container.instance(Config, self._config)
        self._container.alias(Config, "config")

        self._container.singleton(Portal)

        self._container.singleton(ExceptionHandlerContract, ExceptionHandler)

    async def _register_base_service_providers(self) -> None:
        from expanse.http.http_service_provider import HTTPServiceProvider
        from expanse.routing.routing_service_provider import RoutingServiceProvider

        await self.register(HTTPServiceProvider(self._container))
        await self.register(RoutingServiceProvider(self._container))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    try:
                        await self.bootstrap()
                        await self.boot()
                    except Exception as e:
                        await send(
                            {
                                "type": "lifespan.startup.failed",
                                "message": str(e),
                            }
                        )
                        return
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await self._container.terminate()
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        from expanse.core.http.portal import Portal

        portal = await self._container.get(Portal)

        await portal(scope, receive, send)
