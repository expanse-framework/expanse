from expanse.encryption.key import Key
from expanse.encryption.key_generator import KeyGenerator
from expanse.support.secret import Secret


SECRET = b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
SALT = b"73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"


def test_deriving_key_should_generate_a_new_key_of_default_size() -> None:
    key = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT))

    assert isinstance(key.value.reveal(), bytes)
    assert len(key.value.reveal()) == 32
    assert key.value.reveal() != SECRET


def test_deriving_key_should_generate_a_new_key_of_given_size() -> None:
    key = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT), key_size=64)

    assert isinstance(key.value.reveal(), bytes)
    assert len(key.value.reveal()) == 64
    assert key.value.reveal() != SECRET


def test_derived_key_is_different_if_salt_is_different() -> None:
    key = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT))
    key2 = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT))
    other_key = KeyGenerator.generate_key(Key(SECRET), salt=Secret(b"other_salt"))

    assert key.value.reveal() == key2.value.reveal()
    assert key.value.reveal() != other_key.value.reveal()


def test_derived_key_is_different_if_label_is_different() -> None:
    key = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT), purpose=b"foo")
    key2 = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT), purpose=b"bar")
    key3 = KeyGenerator.generate_key(Key(SECRET), salt=Secret(SALT), purpose=b"foo")

    assert key.value.reveal() != key2.value.reveal()
    assert key.value.reveal() == key3.value.reveal()
