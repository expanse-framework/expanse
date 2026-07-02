from pydantic import BaseModel

from expanse.support.secret import Secret


class MyModel(BaseModel):
    secret: Secret[str]
    secret_bytes: Secret[bytes]
    secret_int: Secret[int]


def test_reveal_returns_wrapped_value() -> None:
    secret = Secret("password")

    assert secret.reveal() == "password"


def test_reveal_preserves_non_string_types() -> None:
    secret: Secret[dict[str, int]] = Secret({"token": 42})

    assert secret.reveal() == {"token": 42}


def test_str_does_not_leak_the_value() -> None:
    secret = Secret("password")

    assert str(secret) == "[redacted]"
    assert "password" not in str(secret)


def test_repr_does_not_leak_the_value() -> None:
    secret = Secret("password")

    assert repr(secret) == "Secret('[redacted]')"
    assert "password" not in repr(secret)


def test_secrets_with_equal_values_are_equal() -> None:
    assert Secret("password") == Secret("password")


def test_secrets_with_different_values_are_not_equal() -> None:
    assert Secret("password") != Secret("other")


def test_secret_is_not_equal_to_its_underlying_value() -> None:
    assert Secret("password") != "password"


def test_equality_with_non_secret_returns_not_implemented() -> None:
    secret = Secret("password")

    assert secret != "password"


def test_secret_has_no_dict_attribute() -> None:
    secret = Secret("password")

    assert not hasattr(secret, "__dict__")


def test_secret_can_be_used_in_pydantic_model() -> None:
    m = MyModel(
        secret=Secret("my_secret_value"),
        secret_bytes=Secret(b"my_secret_bytes_value"),
        secret_int=Secret(42),
    )
    m2 = MyModel.model_validate(
        {
            "secret": "my_secret_value",
            "secret_bytes": b"my_secret_bytes_value",
            "secret_int": 42,
        }
    )

    assert m.secret.reveal() == "my_secret_value"
    assert m.secret_bytes.reveal() == b"my_secret_bytes_value"
    assert m.secret_int.reveal() == 42

    assert m2.secret.reveal() == "my_secret_value"
    assert m2.secret_bytes.reveal() == b"my_secret_bytes_value"
    assert m2.secret_int.reveal() == 42
