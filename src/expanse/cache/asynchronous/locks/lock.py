import asyncio
import secrets

from abc import ABC
from abc import abstractmethod
from time import time
from typing import override

from expanse.contracts.lock.asynchronous.lock import Lock as LockContract
from expanse.support._utils import wait_for_event


class Lock(LockContract, ABC):
    def __init__(
        self,
        name: str,
        ttl: int | None = None,
        owner: str | None = None,
        refresh: bool = False,
    ) -> None:
        """
        :param name:
            The name of the lock.
        :param ttl:
            The time to live of the lock in seconds. After this time, the lock will be automatically released.
            If None, the lock will not expire.
        :param owner:
            The owner of the lock. This can be used to identify which worker or process holds the lock.
        :param refresh:
            If True, the lock will be automatically refreshed before it expires if it is owned by the current process.
            This can be useful to prevent the lock from expiring while the process is still working on the task that requires the lock.
        """
        self._name: str = name
        self._ttl: int | None = ttl
        self._sleep_time: float = 0.25
        self._refresh: bool = refresh

        if owner is None:
            owner = secrets.token_urlsafe(32)

        self._owner: str = owner
        self._refreshing_task: asyncio.Task[None] | None = None
        self._stop_refreshing: asyncio.Event = asyncio.Event()

    @override
    async def acquire(self, blocking: bool = True, timeout: int | None = None) -> bool:
        if not blocking and timeout is not None:
            raise ValueError("Cannot specify a timeout when blocking is False")

        start = time()

        while not await self._do_acquire():
            if not blocking:
                return False

            now = time()

            if timeout is not None and now - start >= timeout:
                return False

            await asyncio.sleep(self._sleep_time)

        # Start auto-refreshing the lock if it is enabled and the lock has a TTL.
        if self._refresh and self._ttl is not None:
            self._stop_refreshing.clear()
            self._refreshing_task = asyncio.create_task(self._auto_refresh())

        return True

    @override
    async def release(self, force: bool = False) -> bool:
        """
        Release the lock.

        :param force: If True, forcefully release the lock even if it is not held by the current owner.

        :return: True if the lock was released successfully, False otherwise.
        """
        if self._refreshing_task is not None:
            self._stop_refreshing.set()
            self._refreshing_task.cancel()

        if await self.is_owned_by_current_process() or force:
            return await self._do_release(force=force)

        return False

    @property
    def owner(self) -> str:
        """
        Get the owner of the lock.

        :return: The owner of the lock.
        """
        return self._owner

    @abstractmethod
    async def get_current_owner(self) -> str | None:
        """
        Get the current owner of the lock.

        :return: The current owner of the lock or None if the lock is not currently held by anyone.
        """

    async def is_owned_by(self, owner: str) -> bool:
        """
        Check if the lock is owned by the given owner.

        :param owner: The owner to check against.

        :return: True if the lock is owned by the given owner, False otherwise.
        """
        return await self.get_current_owner() == owner

    async def is_owned_by_current_process(self) -> bool:
        """
        Check if the lock is owned by the current process.

        :return: True if the lock is owned by the current process, False otherwise.
        """
        return await self.is_owned_by(self._owner)

    @abstractmethod
    async def _do_acquire(self) -> bool:
        """
        Attempt to acquire the lock once.

        :param blocking: If True, block until the lock is acquired. If False, return immediately if the lock cannot be acquired.
        :param refresh: If True, prediodically refresh the lock's TTL if it is already owned by the current process.

        :return: True if the lock was acquired successfully, False otherwise.
        """

    @abstractmethod
    async def _do_release(self, force: bool = False) -> bool:
        """
        Attempt to release the lock.

        :param force: If True, forcefully release the lock even if it is not held by the current owner.

        :return: True if the lock was released successfully, False otherwise.
        """

    async def _auto_refresh(self) -> None:
        """
        Automatically refresh the lock's TTL until the lock is released or the process exits.
        """
        assert self._ttl is not None

        interval = self._ttl * 2 / 3

        while not await wait_for_event(self._stop_refreshing, timeout=interval):
            await self.refresh(self._ttl)

    def __del__(self) -> None:
        """
        Ensure that the lock is released when the lock object is garbage collected.
        """
        if self._refreshing_task is not None:
            self._stop_refreshing.set()
            self._refreshing_task.cancel()
