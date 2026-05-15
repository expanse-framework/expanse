import asyncio

from datetime import UTC
from datetime import datetime
from typing import Any
from typing import overload

from expanse.contracts.cache.asynchronous.store import Store


class Cache:
    def __init__(self, store: Store) -> None:
        self._store: Store = store

    async def set(
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
            return await self.delete(key)

        return await self._store.set(key, value, ttl)

    async def set_many(
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
            return await self.delete_many(list(items.keys()))

        return await self._store.set_many(items, ttl)

    @overload
    async def get(self, key: str) -> Any | None: ...

    @overload
    async def get(self, key: str, default: Any) -> Any: ...

    async def get(self, key: str, default: Any | None = None) -> Any | None:
        """
        Retrieve an item from the cache.

        :param key: The key of the item to retrieve.
        :param default: The value to return if the key does not exist in the cache.

        :return: The value associated with the key, or the default value if the key does not exist.
        """
        value = await self._store.get(key)

        if value is None:
            return default

        return value

    async def get_many(self, keys: list[str] | dict[str, Any]) -> dict[str, Any | None]:
        """
        Retrieve multiple items from the cache.

        :param keys: A list of keys to retrieve.
        :param default: The value to return for keys that do not exist in the cache.

        :return: A dictionary mapping each key to its associated value, or the default value if the key does not exist.
        """
        if isinstance(keys, dict):
            keys = list(keys.keys())

        values = await self._store.get_many(keys)

        return {
            key: (
                value
                if value is not None
                else keys[key]
                if isinstance(keys, dict)
                else None
            )
            for key, value in values.items()
        }

    async def has(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        :param key: The key to check for existence.

        :return: True if the key exists in the cache, False otherwise.
        """
        return await self._store.has(key)

    async def pop(self, key: str) -> Any | None:
        """
        Remove an item from the cache and return its value.

        :param key: The key of the item to remove.

        :return: The value associated with the key, or None if the key does not exist.
        """
        value = await self._store.get(key)

        if value is not None:
            await self.delete(key)

        return value

    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        :param key: The key to delete.

        :return: True if the key was successfully deleted, False otherwise.
        """
        return await self._store.delete(key)

    async def delete_many(self, keys: list[str]) -> bool:
        """
        Delete multiple keys from the cache.

        :param keys: The keys to delete.

        :return: True if all keys were successfully deleted, False otherwise.
        """
        tasks = [self.delete(key) for key in keys]

        results = await asyncio.gather(*tasks)

        return all(results)

    async def clear(self) -> bool:
        """
        Clear all items from the cache.
        """
        return await self._store.clear()
