from collections.abc import Buffer
from collections.abc import Iterable
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING

from expanse.configuration.config import Config
from expanse.contracts.storage.synchronous.storage import Storage
from expanse.core.application import Application
from expanse.storage.exceptions import MissingStorageDriverError
from expanse.storage.exceptions import NoDefaultStorageError
from expanse.storage.exceptions import UnconfiguredStorageError
from expanse.storage.exceptions import UnsupportedStorageDriverError


if TYPE_CHECKING:
    from obstore.store import S3Config


class StorageManager(Storage):
    def __init__(self, app: Application, config: Config) -> None:
        self._app: Application = app
        self._config: Config = config
        self._storages: dict[str, Storage] = {}

    def storage(self, name: str | None = None) -> Storage:
        """
        Get a storage instance by name.

        :param name: The name of the storage to retrieve. If None, the default storage will be returned.
        :return: A storage instance.
        """

        if name is None:
            name = self.get_default_storage_name()

        if name in self._storages:
            return self._storages[name]

        storages_configs = self._config.get("storage.storages", {})
        if name not in storages_configs:
            raise UnconfiguredStorageError(f"The storage '{name}' is not configured.")

        storage_config = storages_configs[name]

        storage = self._create_storage(storage_config)

        self._storages[name] = storage

        return storage

    def get_default_storage_name(self) -> str:
        storage_name = self._config.get("storage.storage")
        if storage_name is None:
            raise NoDefaultStorageError("Default storage is not configured.")

        return storage_name

    def get(self, path: str) -> bytes:
        """
        Retrieve the content of a file.

        :param path: The path to the file to retrieve.

        :return: The content of the file.
        """
        return self.storage().get(path)

    def stream(self, path: str, chunk_size: int = 10 * 1024 * 1024) -> Iterator[bytes]:
        return self.storage().stream(path, chunk_size)

    def put(
        self,
        path: str,
        content: (
            IO[bytes] | Path | bytes | Buffer | Iterator[Buffer] | Iterable[Buffer]
        ),
    ) -> None:
        self.storage().put(path, content)

    def delete(self, path: str) -> None:
        self.storage().delete(path)

    def copy(self, source: str, destination: str) -> None:
        self.storage().copy(source, destination)

    def move(self, source: str, destination: str) -> None:
        self.storage().move(source, destination)

    def exists(self, path: str) -> bool:
        return self.storage().exists(path)

    def list(self, prefix: str = "") -> list[str]:
        return self.storage().list(prefix)

    def size(self, path: str) -> int:
        return self.storage().size(path)

    def last_modified(self, path: str) -> datetime:
        return self.storage().last_modified(path)

    def _create_storage(self, raw_config: dict[str, str]) -> Storage:
        driver = raw_config.get("driver")

        if driver is None:
            raise MissingStorageDriverError(
                "Storage driver is not specified in the configuration."
            )

        match driver:
            case "local":
                return self._create_local_storage(raw_config)
            case "s3":
                return self._create_s3_storage(raw_config)
            case _:
                raise UnsupportedStorageDriverError(
                    f"Unsupported storage type: {driver}"
                )

    def _create_local_storage(self, raw_config: dict[str, str]) -> Storage:
        from obstore.store import LocalStore

        from expanse.storage.config.local import LocalStorageConfig
        from expanse.storage.synchronous.storages.storage import (
            Storage as ObStoreStorage,
        )

        config = LocalStorageConfig.model_validate(raw_config)
        root = config.root
        if not root.is_absolute():
            root = self._app.base_path / root

        return ObStoreStorage(LocalStore(root, mkdir=True))

    def _create_s3_storage(self, raw_config: dict[str, str]) -> Storage:
        from obstore.store import S3Store

        from expanse.storage.config.s3 import S3StorageConfig
        from expanse.storage.synchronous.storages.storage import (
            Storage as ObStoreStorage,
        )

        config = S3StorageConfig.model_validate(raw_config)

        params: S3Config = {
            "bucket": config.bucket,
            "access_key_id": config.key,
            "secret_access_key": config.secret,
        }

        if config.region is not None:
            params["region"] = config.region

        if config.endpoint is not None:
            params["endpoint"] = config.endpoint

        return ObStoreStorage(S3Store(**params))
