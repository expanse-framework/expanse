from expanse.support.service_provider import ServiceProvider


class JobsServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.jobs.asynchronous.job_dispatcher import (
            JobDispatcher as AsyncJobDispatcher,
        )
        from expanse.jobs.synchronous.job_dispatcher import (
            JobDispatcher as SyncJobDispatcher,
        )

        self._container.scoped(AsyncJobDispatcher)
        self._container.scoped(SyncJobDispatcher)
