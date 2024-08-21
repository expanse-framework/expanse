from expanse.asynchronous.contracts.debug.exception_renderer import (
    ExceptionRenderer as ExceptionRendererContract,
)
from expanse.asynchronous.exceptions.exception_renderer import ExceptionRenderer
from expanse.asynchronous.support.service_provider import ServiceProvider


class CoreServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.singleton(ExceptionRendererContract, ExceptionRenderer)
