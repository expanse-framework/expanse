from _pytest.monkeypatch import MonkeyPatch

from expanse.assets.config.http import Config
from expanse.http.trusted_header import TrustedHeader


def test_trusted_proxies(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_TRUSTED_PROXIES", "192.1.2.3,192.4.5.6, 192.7.8.9")
    config = Config()

    assert config.trusted_proxies == ["192.1.2.3", "192.4.5.6", "192.7.8.9"]


def test_trusted_headers(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_TRUSTED_HEADERS", "x-forwarded-for, X-Forwarded-Host")
    config = Config()

    assert config.trusted_headers == [
        TrustedHeader.X_FORWARDED_FOR,
        TrustedHeader.X_FORWARDED_HOST,
    ]
