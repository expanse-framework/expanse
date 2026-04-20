import mimetypes
import secrets
import string

from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.contracts.storage.asynchronous.storage_manager import StorageManager
    from expanse.contracts.storage.synchronous.storage_manager import (
        StorageManager as SyncStorageManager,
    )
    from expanse.http._datastructures import RawUploadFile


class UploadFile:
    def __init__(
        self,
        storage_manager: "StorageManager",
        sync_storage_manager: "SyncStorageManager",
        raw_upload_file: "RawUploadFile",
    ) -> None:
        self._storage_manager: StorageManager = storage_manager
        self._sync_storage_manager: SyncStorageManager = sync_storage_manager
        self._raw_upload_file: RawUploadFile = raw_upload_file
        self._hash_name: str | None = None

    @property
    def file(self) -> SpooledTemporaryFile[bytes]:
        return self._raw_upload_file.file

    def save_sync(
        self,
        destination: str | Path,
        *,
        storage: str | None = None,
        name: str | None = None,
    ) -> str:
        """
        Save file to destination, synchronously.

        The file will be saved using the default storage configured, unless a specific storage is provided.
        If no name is provided, a random name will be used.

        :param destination: The directory to save the file to.
        :param storage: The storage to use for saving the file. If None, the default storage will be used.
        :param name: The name to save the file as. If None, a random name will be used.
        """
        file_path = str(Path(destination) / (name or self.hash_name()))

        self._sync_storage_manager.storage(storage).put(
            file_path, self._raw_upload_file.file
        )

        return file_path

    async def save(
        self,
        destination: str | Path,
        *,
        storage: str | None = None,
        name: str | None = None,
    ) -> str:
        """
        Save file to destination.

        The file will be saved using the default storage configured, unless a specific storage is provided.
        If no name is provided, a random name will be used.

        :param destination: The directory to save the file to.
        :param storage: The storage to use for saving the file. If None, the default storage will be used.
        :param name: The name to save the file as. If None, a random name will be used.
        """
        file_path = str(Path(destination) / (name or self.hash_name()))

        await self._storage_manager.storage(storage).put(
            file_path, self._raw_upload_file.file
        )

        return file_path

    def hash_name(self) -> str:
        if self._hash_name is not None:
            return self._hash_name

        self._hash_name = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(40)
        )

        extension: str | None = None
        mime_type = mimetypes.guess_type(self._raw_upload_file.filename)[0]
        if mime_type:
            extension = mimetypes.guess_extension(mime_type)

        if extension:
            return f"{self._hash_name}{extension}"

        return self._hash_name
