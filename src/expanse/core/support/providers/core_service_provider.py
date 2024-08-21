from expanse.contracts.debug.exception_renderer import (
    ExceptionRenderer as ExceptionRendererContract,
)
from expanse.exceptions.exception_renderer import ExceptionRenderer
from expanse.support.service_provider import ServiceProvider


class CoreServiceProvider(ServiceProvider):
    def register(self) -> None:
        self._container.singleton(ExceptionRendererContract, ExceptionRenderer)
