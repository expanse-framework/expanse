from expanse.encryption.key_generator import KeyGenerator


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_deriving_key_should_generate_a_new_key_of_default_size() -> None:
    key = KeyGenerator(SECRET).generate_key(SALT)

    assert isinstance(key, bytes)
    assert len(key) == 32
    assert key != SECRET


def test_deriving_key_should_generate_a_new_key_of_given_size() -> None:
    key = KeyGenerator(SECRET).generate_key(SALT, 64)

    assert isinstance(key, bytes)
    assert len(key) == 64
    assert key != SECRET
