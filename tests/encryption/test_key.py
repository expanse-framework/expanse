from expanse.encryption.key import Key


def test_key_can_be_created() -> None:
    key = Key(b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb")

    assert key.value == b"ZFggd3nBWJcNTUV94n3OpJzDipzC2UZb"
    assert key.id == "5b1b"
