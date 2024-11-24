from __future__ import annotations

import json
import secrets

from collections.abc import Iterator
from collections.abc import MutableMapping
from string import ascii_letters
from string import digits
from typing import TYPE_CHECKING
from typing import Any
from typing import Self

from expanse.session.asynchronous.stores.wrapper import AsyncWrapperStore


if TYPE_CHECKING:
    from expanse.http.request import Request
    from expanse.session.asynchronous.stores.store import AsyncStore as AsyncStore
    from expanse.session.synchronous.stores.store import Store


class HTTPSession(MutableMapping[str, Any]):
    def __init__(
        self,
        name: str,
        store: Store,
        async_store: AsyncStore | None = None,
        id: str | None = None,
    ) -> None:
        self._id = self._validate_id(id)
        self._store = store
        self._async_store = async_store or AsyncWrapperStore(store)
        self._name = name
        self._loaded = False
        self._attributes: dict = {}
        self._request: Request | None = None

    def load(self) -> Self:
        """
        Load the session using the synchronous store.
        """
        if self._loaded:
            return self

        self._load_session()

        self._loaded = True

        return self

    async def async_load(self) -> Self:
        """
        Load the session using the asynchronous store.
        """
        if self._loaded:
            return self

        await self._async_load_session()

        self._loaded = True

        return self

    def save(self) -> None:
        """
        Save the session data using the synchronous store.
        """
        self._store.write(
            self._id, self._serialize(self._attributes), request=self._request
        )

    async def async_save(self) -> None:
        """
        Save the session data using the asynchronous store.
        """
        await self._async_store.write(
            self._id, self._serialize(self._attributes), request=self._request
        )

    def regenerate(self, delete: bool = False) -> Self:
        """
        Generate a new ID for the session and optionally delete it using the synchronous store.
        """
        if delete:
            self._store.delete(self._id)

        self._id = self._generate_id()

        return self

    async def async_regenerate(self, delete: bool = False) -> Self:
        """
        Generate a new ID for the session and optionally delete it using the asynchronous store.
        """
        if delete:
            await self._async_store.delete(self._id)

        self._id = self._generate_id()

        return self

    def get_id(self) -> str:
        """
        Get the session ID.
        """
        return self._id

    def set_id(self, session_id: str | None) -> None:
        """
        Set the session ID.

        The session ID must be a 40-character alphanumeric string.
        It can also be `None` to generate a new session ID.

        :param session_id: The session ID as a 40-character alphanumeric string.
        """
        self._id = self._validate_id(session_id)

    def get_name(self) -> str:
        """
        Get the session cookie name.
        """
        return self._name

    def get(self, key: str, /, default: Any | None = None) -> Any | None:
        return self._attributes.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._attributes[key] = value

    def has(self, key: str) -> bool:
        return key in self._attributes

    def delete(self, key: str) -> None:
        del self._attributes[key]

    def pop(self, key: str, default: Any = None) -> None:
        self._attributes.pop(key, default)

    def all(self) -> dict:
        return self._attributes

    def set_request(self, request: Request) -> None:
        self._request = request

    def _load_session(self) -> None:
        """
        Load the session data from the synchronous store and deserialize it.
        """
        raw_data = self._store.read(self._id)
        self._attributes.update(self._deserialize(raw_data))

    async def _async_load_session(self) -> None:
        """
        Load the session data from the asynchronous store and deserialize it.
        """
        raw_data = await self._async_store.read(self._id)
        self._attributes.update(self._deserialize(raw_data))

    def _validate_id(self, session_id: str | None) -> str:
        if (
            isinstance(session_id, str)
            and session_id.isalnum()
            and len(session_id) == 40
        ):
            return session_id

        return self._generate_id()

    def _generate_id(self) -> str:
        return "".join(secrets.choice(ascii_letters + digits) for _ in range(40))

    def _serialize(self, data: dict) -> str:
        return json.dumps(data)

    def _deserialize(self, data: str) -> dict:
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str, /):
        self.delete(key)

    def __getitem__(self, key: str, /):
        return self._attributes[key]

    def __len__(self) -> int:
        return len(self._attributes)

    def __iter__(self) -> Iterator[str]:
        return iter(self._attributes)
