import pytest

from expanse.http.header_bag import HeaderBag


def test_init() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert "Content-Type" in headers
    assert headers.has("X-Custom")


def test_string_representation() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert str(headers) == """Content-Type: application/json\r\nX-Custom: value\r\n"""

    headers = HeaderBag()

    assert str(headers) == ""


def test_all() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers.all("Content-Type") == ["application/json"]
    assert headers.all("X-Custom") == ["value"]
    assert headers.all() == {
        "content-type": ["application/json"],
        "x-custom": ["value"],
    }


def test_get() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers.get("Content-Type") == "application/json"
    assert headers.get("X-Custom") == "value"
    assert headers.get("Non-Existent", "default") == "default"
    assert headers.get("Non-Existent") is None


def test_set() -> None:
    headers = HeaderBag()

    headers.set("Content-Type", "application/json")
    assert headers.get("Content-Type") == "application/json"

    headers.set("X-Custom", ["value1", "value2"])
    assert headers.get("X-Custom") == "value1"

    headers.set("X-Custom", "value3", replace=False)
    assert headers.get("X-Custom") == "value1"

    headers.set("X-Custom", "value3", replace=True)
    assert headers.get("X-Custom") == "value3"


def test_has() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers.has("Content-Type")
    assert headers.has("X-Custom")
    assert not headers.has("Non-Existent")


def test_remove() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers.has("Content-Type")
    headers.remove("Content-Type")
    assert not headers.has("Content-Type")

    assert headers.has("X-Custom")
    headers.remove("X-Custom")
    assert not headers.has("X-Custom")


def test_getitem() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers["Content-Type"] == "application/json"
    assert headers["X-Custom"] == "value"

    with pytest.raises(KeyError):
        _ = headers["Non-Existent"]


def test_setitem() -> None:
    headers = HeaderBag()

    headers["Content-Type"] = "application/json"
    assert headers["Content-Type"] == "application/json"

    headers["X-Custom"] = ["value1", "value2"]
    assert headers["X-Custom"] == "value1"

    headers["X-Custom"] = "value3"
    assert headers["X-Custom"] == "value3"


def test_delitem() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert headers.has("Content-Type")
    del headers["Content-Type"]
    assert not headers.has("Content-Type")

    assert headers.has("X-Custom")
    del headers["X-Custom"]
    assert not headers.has("X-Custom")


def test_iter() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    header_names = list(headers)
    assert "content-type" in header_names
    assert "x-custom" in header_names
    assert len(header_names) == 2


def test_len() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    assert len(headers) == 2

    headers.set("New-Header", "new-value")
    assert len(headers) == 3

    headers.remove("X-Custom")
    assert len(headers) == 2


def test_repr() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    expected_repr = (
        "HeaderBag({'content-type': ['application/json'], 'x-custom': ['value']})"
    )
    assert repr(headers) == expected_repr

    headers.set("New-Header", "new-value")
    expected_repr = (
        "HeaderBag({'content-type': ['application/json'], 'x-custom': ['value'], "
        "'new-header': ['new-value']})"
    )
    assert repr(headers) == expected_repr


def test_encode() -> None:
    headers = HeaderBag({"Content-Type": "application/json", "X-Custom": "value"})

    encoded_headers = headers.encode()
    assert isinstance(encoded_headers, list)
    assert len(encoded_headers) == 2
    assert encoded_headers[0] == (b"content-type", b"application/json")
    assert encoded_headers[1] == (b"x-custom", b"value")
