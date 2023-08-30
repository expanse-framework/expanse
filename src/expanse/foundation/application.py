from __future__ import annotations

import asyncio
import traceback

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Callable
from typing import ClassVar
from typing import Self

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware as BaseMiddleware

from expanse.container.container import Container
from expanse.foundation.bootstrap.boot_providers import BootProviders
from expanse.foundation.bootstrap.load_configuration import LoadConfiguration
from expanse.foundation.bootstrap.register_providers import RegisterProviders
from expanse.foundation.http.middleware._adapter import AdapterMiddleware
from expanse.routing.routing_service_provider import RoutingServiceProvider
from expanse.support._utils import string_to_class


if TYPE_CHECKING:
    from expanse.foundation.bootstrap.bootstrapper import Bootstrapper
    from expanse.foundation.http.middleware.base import Middleware
    from expanse.support.service_provider import ServiceProvider
    from expanse.types import Receive
    from expanse.types import Scope
    from expanse.types import Send


class Application(Container):
    _bootstrappers: ClassVar[list[type[Bootstrapper]]] = [
        LoadConfiguration,
        RegisterProviders,
        BootProviders,
    ]

    _middleware: ClassVar[list[type[Middleware]]] = []

    _middleware_groups: ClassVar[dict[str, type[Middleware]]] = {}

    def __init__(self, base_path: Path | None = None) -> None:
        super().__init__()

        if base_path is None:
            base_path = Path(traceback.extract_stack(limit=2)[0].filename).parent

        self._base_path: Path = base_path
        self._config_path: Path | None = None
        self._resources_path: Path | None = None

        self._booted: bool = False
        self._has_been_bootstrapped: bool = False
        self._service_providers: list[ServiceProvider] = []
        self._default_bootstrappers: list[
            type[Bootstrapper]
        ] = self.__class__._bootstrappers.copy()
        self._default_middlewares: list[
            type[Middleware]
        ] = self.__class__._middleware.copy()
        self._terminating_callbacks: list[Callable[..., None]] = []

        self._bind_paths()
        self._register_base_bindings()
        self._register_base_service_providers()

        self._app: Starlette = Starlette(debug=True)

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def config_path(self) -> Path:
        return self._config_path or self._base_path.joinpath("config")

    @property
    def resources_path(self) -> Path:
        return self._resources_path or self._base_path.joinpath("resources")

    def is_booted(self) -> bool:
        return self._booted

    def has_been_bootstrapped(self) -> bool:
        return self._has_been_bootstrapped

    def boot(self) -> None:
        """
        Boot the application service providers.
        """
        if self.is_booted():
            return

        for service_provider in self._service_providers:
            self._boot_provider(service_provider)

    def set_base_path(self, base_path: Path) -> Self:
        self._base_path = base_path

        self._bind_paths()

        return self

    def bootstrap(self) -> None:
        try:
            self.bootstrap_with(self._default_bootstrappers)
        except Exception as e:
            print(e)

            raise

    def bootstrap_with(self, bootstrappers: list[type[Bootstrapper]]) -> Self:
        if self._has_been_bootstrapped:
            return self

        for bootstrapper_class in bootstrappers:
            bootstrapper: Bootstrapper = self.make(bootstrapper_class)
            bootstrapper.bootstrap(self)

        self.register_configured_providers()
        self.boot()

        self._has_been_bootstrapped = True

        return self

    def register_configured_providers(self) -> None:
        providers = self.make("config")["app"].get("providers", [])

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

        return provider

    async def terminate(self) -> None:
        for callback in self._terminating_callbacks:
            if asyncio.iscoroutinefunction(callback):
                return await self.call_async(callback)
            else:
                return await run_in_threadpool(self.call, callback)

    def prepend_middleware(self, middleware: type[Middleware]) -> None:
        self._default_middlewares.insert(0, middleware)

    def add_middleware(self, middleware: type[Middleware]) -> None:
        self._default_middlewares.append(middleware)

    def create_scoped_container(self) -> Container:
        return super().create_scoped_container()

    def _bind_paths(self) -> None:
        assert self._base_path is not None

        self.instance("path", self._base_path)
        self.instance("path:config", self.config_path)
        self.instance("path:resources", self.resources_path)

    def _boot_provider(self, provider: ServiceProvider) -> None:
        if hasattr(provider, "boot"):
            self.call(provider.boot)

    def _register_base_bindings(self) -> None:
        self.instance("app", self)
        self.instance(self.__class__, self)
        self.instance(Container, self)

    def _register_base_service_providers(self) -> None:
        self.register(RoutingServiceProvider(self))

    def _setup_router(self) -> None:
        self._app.user_middleware = [
            BaseMiddleware(AdapterMiddleware, middleware=self.make(middleware))
            for middleware in self._default_middlewares
            if hasattr(middleware, "handle")
        ]
        self._app.router = self.make("router")._router

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    self.bootstrap()
                    self._setup_router()
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await self.terminate()
                    await send({"type": "lifespan.shutdown.complete"})
                    return

        await self._app(scope, receive, send)
