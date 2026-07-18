from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from expanse.encryption.encryption_manager import EncryptionManager
from expanse.encryption.encryptor_factory import EncryptorFactory
from expanse.encryption.errors import DecryptionError


if TYPE_CHECKING:
    from expanse.core.application import Application


@pytest.fixture
def manager(app: Application) -> EncryptionManager:
    app.config["app.secret_key"] = "base64:uwyDt6Sezpoa84jCLhvWuLG878Gz3RJvA2_VsNql5EY="
    app.config["app.previous_keys"] = "MG6cMKYU4q3UTine3OT-UiPX-Zp-Ga10"
    app.config["encryption.salt"] = "73NBdlFeA2L1rP-GDasaIFOKYZMIWo07"

    return EncryptionManager(EncryptorFactory(app))


def test_manager_encrypts_and_decrypts_value(manager: EncryptionManager) -> None:
    encrypted = manager.encrypt("Hello, World!")

    assert isinstance(encrypted, str)
    assert manager.decrypt(encrypted) == "Hello, World!"


def test_manager_encrypts_without_compression(manager: EncryptionManager) -> None:
    encrypted = manager.encrypt("Hello, World!", compress=False)

    assert isinstance(encrypted, str)
    assert manager.decrypt(encrypted) == "Hello, World!"


def test_manager_encrypts_and_decrypts_with_purpose(manager: EncryptionManager) -> None:
    encrypted = manager.encrypt("Hello, World!", purpose="cookies")

    assert manager.decrypt(encrypted, purpose="cookies") == "Hello, World!"


def test_manager_decrypt_fails_with_wrong_purpose(manager: EncryptionManager) -> None:
    encrypted = manager.encrypt("Hello, World!", purpose="cookies")

    with pytest.raises(DecryptionError):
        manager.decrypt(encrypted, purpose="sessions")


def test_manager_decrypt_fails_without_purpose_when_encrypted_with_purpose(
    manager: EncryptionManager,
) -> None:
    encrypted = manager.encrypt("Hello, World!", purpose="cookies")

    with pytest.raises(DecryptionError):
        manager.decrypt(encrypted)


def test_manager_decrypt_fails_with_purpose_when_encrypted_without_purpose(
    manager: EncryptionManager,
) -> None:
    encrypted = manager.encrypt("Hello, World!")

    with pytest.raises(DecryptionError):
        manager.decrypt(encrypted, purpose="cookies")
