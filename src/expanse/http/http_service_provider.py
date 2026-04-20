from expanse.contracts.storage.asynchronous.storage_manager import StorageManager
from expanse.contracts.storage.synchronous.storage_manager import (
    StorageManager as SyncStorageManager,
)
from expanse.http._datastructures import RawUploadFile
from expanse.http.exceptions import NoUploadFileFoundError
from expanse.http.request import Request
from expanse.http.response_adapter import ResponseAdapter
from expanse.http.upload_file import UploadFile
from expanse.support.service_provider import ServiceProvider


class HTTPServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self._container.scoped(ResponseAdapter)
        self._container.scoped(UploadFile, self._retrieve_upload_file)

    async def _retrieve_upload_file(
        self,
        storage_manager: StorageManager,
        sync_storage_manager: SyncStorageManager,
        request: Request,
        name: str | None = None,
    ) -> UploadFile:
        form_data = await request.form
        if name is not None:
            file = form_data.get(name)
            if isinstance(file, RawUploadFile):
                return UploadFile(storage_manager, sync_storage_manager, file)

            raise NoUploadFileFoundError(f"File upload '{name}' does not exist.")
        else:
            for value in form_data.values():
                if isinstance(value, RawUploadFile):
                    return UploadFile(storage_manager, sync_storage_manager, value)

            raise NoUploadFileFoundError("No uploaded file found in the form data.")
