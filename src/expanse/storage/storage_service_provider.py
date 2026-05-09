from expanse.contracts.storage.asynchronous.storage import Storage
from expanse.contracts.storage.asynchronous.storage_manager import (
    StorageManager as StorageManagerContract,
)
from expanse.contracts.storage.synchronous.storage import Storage as SyncStorage
from expanse.contracts.storage.synchronous.storage_manager import (
    StorageManager as SyncStorageManagerContract,
)
from expanse.support.service_provider import ServiceProvider


class StorageServiceProvider(ServiceProvider):
    async def register(self) -> None:
        from expanse.storage.asynchronous.storage_manager import StorageManager
        from expanse.storage.synchronous.storage_manager import (
            StorageManager as SyncStorageManager,
        )

        self._container.singleton(StorageManagerContract, StorageManager)
        self._container.scoped(Storage, self._create_storage)

        self._container.singleton(SyncStorageManagerContract, SyncStorageManager)
        self._container.scoped(SyncStorage, self._create_sync_storage)

    async def _create_storage(
        self, manager: StorageManagerContract, name: str | None = None
    ) -> Storage:
        storage = manager.storage(name)

        return storage

    async def _create_sync_storage(
        self, manager: SyncStorageManagerContract, name: str | None = None
    ) -> SyncStorage:
        storage = manager.storage(name)

        return storage
