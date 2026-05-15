from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any
from typing import overload


if TYPE_CHECKING:
    from expanse.contracts.cache.synchronous.store import Store


class Cache:
    def __init__(self, store: Store) -> None:
        self._store: Store = store

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store an item in the cache.

        :param key: The key under which the value should be stored.
        :param value: The value to be stored.
        :param ttl: The time-to-live (TTL) for the cache item in seconds.
        :param until: The datetime until which the cache item should be valid.

        :return: True if the item was successfully stored, False otherwise.
        """
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        if ttl is not None and ttl <= 0:
            return self.delete(key)

        return self._store.set(key, value, ttl)

    def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        until: datetime | None = None,
    ) -> bool:
        """
        Store multiple items in the cache.

        :param items: A dictionary of key-value pairs to be stored.
        :param ttl: The time-to-live (TTL) for the cache items in seconds.
        :param until: The datetime until which the cache items should be valid.

        :return: True if the items were successfully stored, False otherwise.
        """
        if ttl is not None and until is not None:
            raise ValueError("Cannot specify both 'ttl' and 'until' parameters.")

        if until is not None:
            ttl = int((until - datetime.now(UTC)).total_seconds())

        if ttl is not None and ttl <= 0:
            return self.delete_many(list(items.keys()))

        return self._store.set_many(items, ttl)

    @overload
    def get(self, key: str) -> Any | None: ...

    @overload
    def get(self, key: str, default: Any) -> Any: ...

    def get(self, key: str, default: Any | None = None) -> Any | None:
        """
        Retrieve an item from the cache.

        :param key: The key of the item to retrieve.
        :param default: The value to return if the key does not exist in the cache.

        :return: The value associated with the key, or the default value if the key does not exist.
        """
        value = self._store.get(key)

        if value is None:
            return default

        return value

    def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        """
        Retrieve multiple items from the cache.

        :param keys: A list of keys to retrieve.

        :return: A dictionary mapping each key to its associated value, or None if the key does not exist.
        """
        if isinstance(keys, dict):
            keys = list(keys.keys())

        values = self._store.get_many(keys)

        return dict(values.items())

    def has(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        :param key: The key to check for existence.

        :return: True if the key exists in the cache, False otherwise.
        """
        return self._store.has(key)

    def pop(self, key: str) -> Any | None:
        """
        Remove an item from the cache and return its value.

        :param key: The key of the item to remove.

        :return: The value associated with the key, or None if the key does not exist.
        """
        value = self._store.get(key)

        if value is not None:
            self.delete(key)

        return value

    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        :param key: The key to delete.

        :return: True if the key was successfully deleted, False otherwise.
        """
        return self._store.delete(key)

    def delete_many(self, keys: list[str]) -> bool:
        """
        Delete multiple keys from the cache.

        :param keys: The keys to delete.

        :return: True if all keys were successfully deleted, False otherwise.
        """
        return all(self.delete(key) for key in keys)

    def clear(self) -> bool:
        """
        Clear all items from the cache.
        """
        return self._store.clear()
