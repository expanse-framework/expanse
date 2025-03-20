from datetime import datetime
from datetime import timezone

import pytest

from expanse.http.cookie import Cookie
from expanse.http.cookie import SameSite
from expanse.http.exceptions import CookieError


@pytest.mark.parametrize(
    "name",
    [
        ",name",
        ";name",
        " name",
        "\tname",
        "\nname",
        "\rname",
        "\013name",
        "\014name",
    ],
)
def test_cookies_can_be_instantiated_with_special_characters_in_name(name: str) -> None:
    cookie = Cookie(name, "value")

    assert cookie.name == name
    assert cookie.value == "value"


def test_cookies_cannot_have_empty_names() -> None:
    with pytest.raises(CookieError):
        Cookie("", "value")


def test_cookies_cannot_have_a_negative_expiration() -> None:
    cookie = Cookie("name", "value", expires=-100)

    assert cookie.expires == 0


def test_cookies_get_value() -> None:
    cookie = Cookie("name", "value")

    assert cookie.value == "value"
    assert cookie.with_value("other_value").value == "other_value"


def test_cookies_get_path() -> None:
    cookie = Cookie("name", "value", path="/path")

    assert cookie.path == "/path"

    assert cookie.with_path("/").path == "/"
    assert cookie.with_path("").path == "/"


def test_cookies_get_expires() -> None:
    cookie = Cookie("name", "value")

    assert cookie.expires == 0

    cookie = Cookie("name", "value", expires=1740787200)

    assert cookie.expires == 1740787200

    cookie = Cookie(
        "name",
        "value",
        expires=datetime(
            year=2025,
            month=3,
            day=12,
            hour=12,
            minute=34,
            second=56,
            tzinfo=timezone.utc,
        ),
    )

    assert cookie.expires == 1741782896

    assert cookie.with_expires(0).expires == 0


def test_cookies_get_domain() -> None:
    cookie = Cookie("name", "value", domain="example.com")

    assert cookie.domain == "example.com"

    assert cookie.with_domain("example.org").domain == "example.org"


def test_cookies_is_secure() -> None:
    cookie = Cookie("name", "value", secure=True)

    assert cookie.is_secure()

    cookie = Cookie("name", "value", secure=False)

    assert not cookie.is_secure()

    assert cookie.with_secure().is_secure()


def test_cookies_is_http_only() -> None:
    cookie = Cookie("name", "value", http_only=True)

    assert cookie.is_http_only()

    cookie = Cookie("name", "value", http_only=False)

    assert not cookie.is_http_only()

    assert cookie.with_http_only().is_http_only()


def test_cookies_is_partitioned() -> None:
    cookie = Cookie("name", "value", partitioned=True)

    assert cookie.is_partitioned()

    cookie = Cookie("name", "value", partitioned=False)

    assert not cookie.is_partitioned()

    assert cookie.with_partitioned().is_partitioned()


def test_cookies_get_same_site() -> None:
    cookie = Cookie("name", "value")

    assert cookie.same_site == SameSite.LAX

    assert cookie.with_same_site(SameSite.STRICT).same_site == SameSite.STRICT


def test_cookies_to_string() -> None:
    cookie = Cookie(
        "name",
        "value",
        expires=1741782896,
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=None,
    )
    expected = "name=value; expires=Wed, 12 Mar 2025 12:34:56 GMT; Max-Age=0; domain=example.com; path=/; secure; httponly"

    assert (
        str(cookie) == expected
    ), "__str__() returns the correct string representation"

    cookie = Cookie(
        "name",
        "value with spaces",
        expires=1741782896,
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=None,
    )
    expected = 'name="value with spaces"; expires=Wed, 12 Mar 2025 12:34:56 GMT; Max-Age=0; domain=example.com; path=/; secure; httponly'

    assert str(cookie) == expected, "__str__() properly quotes values with spaces"

    cookie = Cookie(
        "name",
        None,
        expires=1741782896,
        domain="example.com",
        path="/path",
        secure=True,
        http_only=True,
        same_site=None,
    )
    expected = "name=deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; domain=example.com; path=/path; secure; httponly"

    assert (
        str(cookie) == expected
    ), "__str__() returns the correct string representation for cleared cookies"

    cookie = Cookie(
        "name",
        "value with spaces",
        expires=1741782896,
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=SameSite.STRICT,
    )
    expected = 'name="value with spaces"; expires=Wed, 12 Mar 2025 12:34:56 GMT; Max-Age=0; domain=example.com; path=/; secure; httponly; samesite=strict'

    assert (
        str(cookie) == expected
    ), "__str__() returns the correct string representation with same site"

    cookie = Cookie(
        "name",
        "value with spaces",
        expires=1741782896,
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=SameSite.STRICT,
        partitioned=True,
    )
    expected = 'name="value with spaces"; expires=Wed, 12 Mar 2025 12:34:56 GMT; Max-Age=0; domain=example.com; path=/; secure; httponly; samesite=strict; partitioned'

    assert (
        str(cookie) == expected
    ), "__str__() returns the correct string representation with partitioned cookies"


def test_cookies_set_secure_default() -> None:
    cookie = Cookie("name", "value")

    assert not cookie.is_secure()

    cookie = cookie.set_secure_default(True)

    assert cookie.is_secure()


def test_cookies_repr() -> None:
    cookie = Cookie(
        "name",
        "value",
        expires=1741782896,
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
        same_site=None,
    )
    expected = "<Cookie name=value; expires=Wed, 12 Mar 2025 12:34:56 GMT; Max-Age=0; domain=example.com; path=/; secure; httponly>"

    assert repr(cookie) == expected
