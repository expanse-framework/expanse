from __future__ import annotations

import json
import secrets

from collections.abc import Iterator
from collections.abc import MutableMapping
from collections.abc import Sequence
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

    @property
    def csrf_token(self) -> str | None:
        return self.get("_csrf_token")

    def load(self) -> Self:
        """
        Load the session using the synchronous store.
        """
        self._load_session()

        if not self.has("_csrf_token"):
            self.regenerate_csrf_token()

        self._loaded = True

        return self

    async def async_load(self) -> Self:
        """
        Load the session using the asynchronous store.
        """
        await self._async_load_session()

        if not self.has("_csrf_token"):
            self.regenerate_csrf_token()

        self._loaded = True

        return self

    def save(self) -> None:
        """
        Save the session data using the synchronous store.
        """
        self.ripen_flash_data()

        self._store.write(
            self._id, self._serialize(self._attributes), request=self._request
        )

    async def async_save(self) -> None:
        """
        Save the session data using the asynchronous store.
        """
        self.ripen_flash_data()

        await self._async_store.write(
            self._id, self._serialize(self._attributes), request=self._request
        )

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

    def get_csrf_token(self) -> str | None:
        """
        Get the CSRF token.
        """
        return self.get("_csrf_token")

    def is_loaded(self) -> bool:
        """
        Check if the session has been loaded.
        """
        return self._loaded

    def get(self, key: str, /, default: Any | None = None) -> Any:
        attributes: dict[str, Any] = self._attributes

        parts = key.split(".")
        for part in parts:
            if part not in attributes:
                return default

            attributes = attributes[part]

        return attributes

    def set(self, key: str, value: Any) -> None:
        attributes: dict[str, Any] = self._attributes

        parts = key.split(".")
        count = len(parts)
        for i, part in enumerate(parts):
            if i == count - 1:
                attributes[part] = value
                return

            if part not in attributes:
                attributes[part] = {}

            attributes = attributes[part]

    def has(self, key: str) -> bool:
        attributes: dict[str, Any] = self._attributes

        parts = key.split(".")
        for part in parts:
            if part not in attributes:
                return False

            attributes = attributes[part]

        return True

    def delete(self, *keys: str) -> None:
        for key in keys:
            self._delete_key(key)

    def pop(self, key: str, default: Any = None) -> None:
        self._attributes.pop(key, default)

    def all(self) -> dict:
        return self._attributes

    def clear(self) -> None:
        self._attributes = {}

    def append(self, key: str, value: Any) -> None:
        if key not in self._attributes:
            self._attributes[key] = []

        self._attributes[key].append(value)

    def flash(self, key: str, value: Any) -> None:
        self.set(key, value)

        flash_data: list[str] = self.get("_flash.new", [])
        if key not in flash_data:
            flash_data.append(key)

        self.set("_flash.new", flash_data)

        self._delete_from_old_flash_data(key)

    def reflash(self, only: Sequence[str] | None) -> None:
        """
        Reflash the existing flash data.
        """
        if only is None:
            self._add_to_new_flash_data(*self.get("_flash.old", []))
            self.set("_flash.old", [])
        else:
            self._add_to_new_flash_data(*only)
            self._delete_from_old_flash_data(*only)

    def ripen_flash_data(self) -> None:
        self.delete(*self.get("_flash.old", []))
        self.set("_flash.old", self.get("_flash.new", []))
        self.set("_flash.new", [])

    def invalidate(self) -> None:
        """
        Invalidate the session and delete it from the synchronous store.
        """
        self.clear()

        return self.generate_new_id(delete=True)

    async def async_invalidate(self) -> None:
        """
        Invalidate the session and delete it from the asynchronous store.
        """
        self.clear()

        return await self.async_generate_new_id(delete=True)

    def regenerate(self, delete: bool = False) -> None:
        """
        Generate a new ID for the session and optionally delete it using the synchronous store.

        This method also regenerates the CSRF token.
        """
        self.generate_new_id(delete=delete)

        self.regenerate_csrf_token()

    async def async_regenerate(self, delete: bool = False) -> None:
        """
        Generate a new ID for the session and optionally delete it using the asynchronous store.

        This method also regenerates the CSRF token.
        """
        await self.async_generate_new_id(delete=delete)

        self.regenerate_csrf_token()

    def generate_new_id(self, delete: bool = False) -> None:
        """
        Generate a new ID for the session and optionally delete the old one.

        :param delete: Whether to delete the old session or not.
        """
        if delete:
            self._store.delete(self._id)

        self.set_id(self._generate_id())

    async def async_generate_new_id(self, delete: bool = False) -> None:
        """
        Generate a new ID for the session and optionally delete the old one using the asynchronous store.

        :param delete: Whether to delete the old session or not.
        """
        if delete:
            self._store.delete(self._id)

        self.set_id(self._generate_id())

    def regenerate_csrf_token(self) -> None:
        """
        Regenerate the CSRF token.
        """
        self.set("_csrf_token", self._generate_csrf_token())

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

    def _generate_csrf_token(self) -> str:
        return secrets.token_urlsafe(40)

    def _serialize(self, data: dict) -> str:
        return json.dumps(data)

    def _deserialize(self, data: str) -> dict:
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _add_to_new_flash_data(self, *keys: str) -> None:
        flash_data: list[str] = self.get("_flash.new", [])

        flash_data.extend([key for key in keys if key not in flash_data])

        self.set("_flash.new", flash_data)

    def _delete_from_old_flash_data(self, *keys: str) -> None:
        flash_data: list[str] = self.get("_flash.old", [])

        flash_data = [key for key in flash_data if key not in keys]

        self.set("_flash.old", flash_data)

    def _delete_key(self, key: str) -> None:
        parts = key.split(".")
        count = len(parts)
        attributes: dict[str, Any] = self._attributes
        for i, part in enumerate(parts):
            if i == count - 1:
                del attributes[part]
                return

            attributes = attributes[part]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str, /):
        self.delete(key)

    def __getitem__(self, key: str, /):
        _missing = object()
        value = self.get(key, _missing)

        if value is _missing:
            raise KeyError(key)

        return value

    def __len__(self) -> int:
        return len(self._attributes)

    def __iter__(self) -> Iterator[str]:
        return iter(self._attributes)

    def __contains__(self, key: str) -> bool:  # type: ignore[override]
        return self.has(key)
