from expanse.encryption.key import Key
from expanse.encryption.key_generator import KeyGenerator


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_deriving_key_should_generate_a_new_key_of_default_size() -> None:
    key = KeyGenerator(SALT).generate_key(Key(SECRET))

    assert isinstance(key.value, bytes)
    assert len(key.value) == 32
    assert key.value != SECRET


def test_deriving_key_should_generate_a_new_key_of_given_size() -> None:
    key = KeyGenerator(SALT).generate_key(Key(SECRET), 64)

    assert isinstance(key.value, bytes)
    assert len(key.value) == 64
    assert key.value != SECRET


def test_derived_key_is_different_if_salt_is_different() -> None:
    key = KeyGenerator(SALT).generate_key(Key(SECRET))
    key2 = KeyGenerator(SALT).generate_key(Key(SECRET))
    other_key = KeyGenerator(b"other_salt").generate_key(Key(SECRET))

    assert key.value == key2.value
    assert key.value != other_key.value


def test_derived_key_is_different_if_label_is_different() -> None:
    key = KeyGenerator(SALT, label=b"foo").generate_key(Key(SECRET))
    key2 = KeyGenerator(SALT, label=b"bar").generate_key(Key(SECRET))
    key3 = KeyGenerator(SALT, label=b"foo").generate_key(Key(SECRET))

    assert key.value != key2.value
    assert key.value == key3.value
