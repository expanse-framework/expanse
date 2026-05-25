from __future__ import annotations

import secrets
import threading

from abc import ABC
from abc import abstractmethod
from time import sleep
from time import time
from typing import override

from expanse.contracts.lock.synchronous.lock import Lock as LockContract


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
        """
        self._name: str = name
        self._ttl: int | None = ttl
        self._sleep_time: float = 0.25
        self._refresh: bool = refresh

        if owner is None:
            owner = secrets.token_urlsafe(32)

        self._owner: str = owner
        self._refreshing_thread: threading.Thread | None = None
        self._stop_refreshing: threading.Event = threading.Event()

    @override
    def acquire(self, blocking: bool = True, timeout: int | None = None) -> bool:
        if not blocking and timeout is not None:
            raise ValueError("Cannot specify a timeout when blocking is False")

        start = time()

        while not self._do_acquire():
            if not blocking:
                return False

            now = time()

            if timeout is not None and now - start >= timeout:
                return False

            sleep(self._sleep_time)

        if self._refresh and self._ttl is not None:
            self._stop_refreshing.clear()
            self._refreshing_thread = threading.Thread(
                target=self._auto_refresh, daemon=True
            )
            self._refreshing_thread.start()

        return True

    @override
    def release(self, force: bool = False) -> bool:
        """
        Release the lock.

        :param force: If True, forcefully release the lock even if it is not held by the current owner.

        :return: True if the lock was released successfully, False otherwise.
        """
        if self._refreshing_thread is not None:
            self._stop_refreshing.set()
            self._refreshing_thread = None

        if self.is_owned_by_current_process() or force:
            return self._do_release(force=force)

        return False

    @property
    def owner(self) -> str:
        return self._owner

    @abstractmethod
    def get_current_owner(self) -> str | None:
        """
        Get the current owner of the lock.

        :return: The current owner of the lock or None if the lock is not currently held by anyone.
        """

    def is_owned_by(self, owner: str) -> bool:
        return self.get_current_owner() == owner

    def is_owned_by_current_process(self) -> bool:
        return self.is_owned_by(self._owner)

    @abstractmethod
    def _do_acquire(self) -> bool:
        """
        Attempt to acquire the lock once.

        :return: True if the lock was acquired successfully, False otherwise.
        """

    @abstractmethod
    def _do_release(self, force: bool = False) -> bool:
        """
        Attempt to release the lock.

        :param force: If True, forcefully release the lock even if it is not held by the current owner.

        :return: True if the lock was released successfully, False otherwise.
        """

    def _auto_refresh(self) -> None:
        assert self._ttl is not None

        interval = self._ttl * 2 / 3

        while not self._stop_refreshing.wait(timeout=interval):
            self.refresh(self._ttl)

    def __del__(self) -> None:
        self.release(force=True)
