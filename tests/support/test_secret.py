from expanse.support.secret import Secret


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
