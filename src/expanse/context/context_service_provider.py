from expanse.support.service_provider import ServiceProvider


class ContextServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.context.context import Context

        self._container.scoped(Context)
