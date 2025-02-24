from expanse.encryption.key import Key
from expanse.encryption.key_generator import KeyGenerator


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_deriving_key_should_generate_a_new_key_of_default_size() -> None:
    key = KeyGenerator(Key(SECRET)).generate_key(SALT)

    assert isinstance(key.value, bytes)
    assert len(key.value) == 32
    assert key.value != SECRET


def test_deriving_key_should_generate_a_new_key_of_given_size() -> None:
    key = KeyGenerator(Key(SECRET)).generate_key(SALT, 64)

    assert isinstance(key.value, bytes)
    assert len(key.value) == 64
    assert key.value != SECRET
