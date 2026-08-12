import re
import string
import time

from datetime import datetime
from enum import StrEnum
from functools import cached_property
from time import gmtime
from time import strftime
from types import EllipsisType
from typing import Final
from typing import Self

from expanse.http.exceptions import CookieError


_UNSET = object()


_cookie_legal_chars: Final[str] = (
    string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~:"
)
_cookie_is_legal_key = re.compile(f"[{re.escape(_cookie_legal_chars)}]+").fullmatch
_cookie_translator: Final[dict[int, str]] = {
    **{
        n: f"\\{n:03o}"
        for n in set(range(256)) - set(map(ord, _cookie_legal_chars + " ()/<=>?@[]{}"))
    },
    ord('"'): '\\"',
    ord("\\"): "\\\\",
}


class SameSite(StrEnum):
    LAX = "lax"
    STRICT = "strict"
    NONE = "none"


class Cookie:
    def __init__(
        self,
        name: str,
        value: str | None = None,
        expires: int | datetime = 0,
        domain: str | None = None,
        path: str | None = None,
        secure: bool | None = None,
        http_only: bool = False,
        same_site: SameSite | None = SameSite.LAX,
        partitioned: bool = False,
    ) -> None:
        """
        :param name: The name of the cookie.
        :param value: The value of the cookie.
        :param expires: The time the cookie expires.
        :param domain: The domain the cookie is available to.
        :param path: The path on the server in which the cookie will be available on.
        :param secure: Whether the client should send back the cookie only over HTTPS
                       or None to auto-enable this when the request is already using HTTPS.
        :param http_only: Whether the cookie will be made accessible only through the HTTP protocol.
        :param same_site: Whether the cookie will be available for cross-site requests.
        :param partitioned: Whether the cookie is partitioned or not.
        """
        if not name:
            raise CookieError("The cookie name cannot be empty.")

        self._name = name
        self._value = value
        self._expires: int = self._compute_expires(expires)
        self._domain = domain
        self._path = path or "/"
        self._secure = secure
        self._http_only = http_only
        self._same_site = same_site
        self._partitioned = partitioned
        self._secure_default: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str | None:
        return self._value

    @property
    def expires(self) -> int:
        return self._expires

    @property
    def domain(self) -> str | None:
        return self._domain

    @property
    def path(self) -> str:
        return self._path

    def is_secure(self) -> bool:
        if self._secure is None:
            return self._secure_default

        return self._secure

    def is_http_only(self) -> bool:
        return self._http_only

    @property
    def same_site(self) -> SameSite | None:
        return self._same_site

    def is_partitioned(self) -> bool:
        return self._partitioned

    @cached_property
    def max_age(self) -> int:
        max_age: int = int(self._expires - time.time())

        return max_age if max_age > 0 else 0

    def with_value(self, value: str | None) -> Self:
        """
        Creates a copy of the cookie with a new value.

        :param value: The value of the cookie.
        """
        return self._clone(value=value)

    def with_expires(self, expires: int | datetime) -> Self:
        """
        Creates a copy of the cookie with a new expiration time.

        :param expires: The time the cookie expires.
        """
        return self._clone(expires=expires)

    def with_domain(self, domain: str | None) -> Self:
        """
        Creates a copy of the cookie with a new domain.

        :param domain: The domain the cookie is available to.
        """
        return self._clone(domain=domain)

    def with_path(self, path: str) -> Self:
        """
        Creates a copy of the cookie with a new path.

        :param path: The path on the server in which the cookie will be available on.
        """
        return self._clone(path=path or "/")

    def with_secure(self, secure: bool = True) -> Self:
        """
        Creates a copy of the cookie with a new secure flag.

        :param secure: Whether the client should send back the cookie only over HTTPS.
        """
        return self._clone(secure=secure)

    def with_http_only(self, http_only: bool = True) -> Self:
        """
        Creates a copy of the cookie with a new HTTP only flag.

        :param http_only: Whether the cookie will be made accessible only through the HTTP protocol.
        """
        return self._clone(http_only=http_only)

    def with_same_site(self, same_site: SameSite) -> Self:
        """
        Creates a copy of the cookie with a new SameSite attribute.

        :param same_site: Whether the cookie will be available for cross-site requests.
        """
        return self._clone(same_site=same_site)

    def with_partitioned(self, partitioned: bool = True) -> Self:
        """
        Creates a copy of the cookie with a new partitioned flag.

        :param partitioned: Whether the cookie is partitioned or not.
        """
        return self._clone(partitioned=partitioned)

    def set_secure_default(self, secure: bool) -> Self:
        self._secure_default = secure

        return self

    def _clone(
        self,
        value: str | None | EllipsisType = ...,
        expires: int | datetime | EllipsisType = ...,
        domain: str | None | EllipsisType = ...,
        path: str | None | EllipsisType = ...,
        secure: bool | EllipsisType = ...,
        http_only: bool | EllipsisType = ...,
        same_site: SameSite | EllipsisType = ...,
        partitioned: bool | EllipsisType = ...,
    ) -> Self:
        return self.__class__(
            self._name,
            self._value if value is ... else value,
            self._expires if expires is ... else expires,
            self._domain if domain is ... else domain,
            self._path if path is ... else path,
            self._secure if secure is ... else secure,
            self._http_only if http_only is ... else http_only,
            self._same_site if same_site is ... else same_site,
            self._partitioned if partitioned is ... else partitioned,
        )

    def _compute_expires(self, expires: int | datetime) -> int:
        if isinstance(expires, datetime):
            expires = int(expires.timestamp())

        if expires < 0:
            expires = 0

        return expires

    def _quote(self, value: str) -> str:
        """
        Quote a string for use in a cookie header.

        If the string does not need to be double-quoted, then just return the
        string.  Otherwise, surround the string in double quotes and quote
        (with a "\") special characters.
        """
        if _cookie_is_legal_key(value):
            return value
        else:
            return '"' + value.translate(_cookie_translator) + '"'

    def __str__(self) -> str:
        parts = [f"{self._quote(self._name)}", "="]

        if not self._value:
            parts.append("deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0")
        else:
            parts.append(self._quote(self._value))

            if self._expires:
                expires = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(self._expires))
                parts.append(f"; expires={expires}; Max-Age={self.max_age}")

        if self._domain:
            parts.append(f"; domain={self._domain}")

        if self._path:
            parts.append(f"; path={self._path}")

        if self.is_secure():
            parts.append("; secure")

        if self.is_http_only():
            parts.append("; httponly")

        if self._same_site:
            parts.append(f"; samesite={self._same_site}")

        if self.is_partitioned():
            parts.append("; partitioned")

        return "".join(parts)

    def __bytes__(self) -> bytes:
        return str(self).encode("ascii")

    def __repr__(self):
        return f"<Cookie {self.__str__()}>"
