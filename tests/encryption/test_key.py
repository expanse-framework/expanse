from expanse.encryption.key import Key
from expanse.support.secret import Secret


def test_key_can_be_created() -> None:
    key = Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")

    assert key.value.reveal() == b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
    assert key.id == "3d285baf"


def test_key_can_be_created_with_secret() -> None:
    key = Key(Secret(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"))

    assert key.value.reveal() == b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
    assert key.id == "3d285baf"
