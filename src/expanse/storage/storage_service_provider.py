from expanse.contracts.storage.asynchronous.storage import Storage
from expanse.contracts.storage.asynchronous.storage_manager import (
    StorageManager as StorageManagerContract,
)
from expanse.support.service_provider import ServiceProvider


class StorageServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.storage.asynchronous.storage_manager import StorageManager

        self._container.singleton(StorageManagerContract, StorageManager)
        self._container.scoped(Storage, self._create_storage)

    async def _create_storage(
        self, manager: StorageManagerContract, name: str | None = None
    ) -> Storage:
        storage = manager.storage(name)

        return storage
