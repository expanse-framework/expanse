from expanse.support.service_provider import ServiceProvider


class QueueServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.queue.asynchronous.job_dispatcher import AsyncJobDispatcher
        from expanse.queue.synchronous.job_dispatcher import JobDispatcher

        self._container.scoped(AsyncJobDispatcher)
        self._container.scoped(JobDispatcher)
