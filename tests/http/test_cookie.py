from datetime import datetime
from datetime import timezone

import pytest

from expanse.http.cookie import Cookie
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

    assert cookie.expires == datetime(year=1970, month=1, day=1, tzinfo=timezone.utc)
