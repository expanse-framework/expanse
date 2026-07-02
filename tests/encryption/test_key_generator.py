from expanse.encryption.key import Key
from expanse.encryption.key_generator import KeyGenerator
from expanse.support.secret import Secret


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_deriving_key_should_generate_a_new_key_of_default_size() -> None:
    key = KeyGenerator(Secret(SALT)).generate_key(Key(SECRET))

    assert isinstance(key.value.reveal(), bytes)
    assert len(key.value.reveal()) == 32
    assert key.value.reveal() != SECRET


def test_deriving_key_should_generate_a_new_key_of_given_size() -> None:
    key = KeyGenerator(Secret(SALT)).generate_key(Key(SECRET), 64)

    assert isinstance(key.value.reveal(), bytes)
    assert len(key.value.reveal()) == 64
    assert key.value.reveal() != SECRET


def test_derived_key_is_different_if_salt_is_different() -> None:
    key = KeyGenerator(Secret(SALT)).generate_key(Key(SECRET))
    key2 = KeyGenerator(Secret(SALT)).generate_key(Key(SECRET))
    other_key = KeyGenerator(Secret(b"other_salt")).generate_key(Key(SECRET))

    assert key.value.reveal() == key2.value.reveal()
    assert key.value.reveal() != other_key.value.reveal()


def test_derived_key_is_different_if_label_is_different() -> None:
    key = KeyGenerator(Secret(SALT), label=b"foo").generate_key(Key(SECRET))
    key2 = KeyGenerator(Secret(SALT), label=b"bar").generate_key(Key(SECRET))
    key3 = KeyGenerator(Secret(SALT), label=b"foo").generate_key(Key(SECRET))

    assert key.value.reveal() != key2.value.reveal()
    assert key.value.reveal() == key3.value.reveal()
