from abc import ABC
from abc import abstractmethod

from expanse.contracts.storage.synchronous.storage import Storage


class StorageManager(ABC):
    @abstractmethod
    def storage(self, name: str | None = None) -> Storage:
        """
        Get a storage instance by name.

        :param name: The name of the storage to retrieve. If None, the default storage will be returned.
        :return: A storage instance.
        """
