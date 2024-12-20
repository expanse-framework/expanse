from expanse.container.container import Container
from expanse.http.request import Request
from expanse.http.response_adapter import ResponseAdapter
from expanse.support.service_provider import ServiceProvider
from expanse.view.view_factory import AsyncViewFactory
from expanse.view.view_factory import ViewFactory


class HTTPServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.scoped(ResponseAdapter)

        await self._container.on_resolved(ViewFactory, self._register_view_locals)
        await self._container.on_resolved(
            AsyncViewFactory, self._register_async_view_locals
        )

    async def _register_view_locals(
        self, factory: ViewFactory, container: Container
    ) -> None:
        if container.has(Request):
            factory.register_local(
                request=await container.get(Request),
            )

    async def _register_async_view_locals(
        self, factory: AsyncViewFactory, container: Container
    ) -> None:
        if container.has(Request):
            factory.register_local(
                request=await container.get(Request),
            )
