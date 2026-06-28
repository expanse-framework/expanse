from expanse.encryption.encryptor_factory import EncryptorFactory


class EncryptionManager:
    def __init__(self, factory: EncryptorFactory) -> None:
        self._factory: EncryptorFactory = factory

    def encrypt(
        self, value: str, *, purpose: str | None = None, compress: bool = True
    ) -> str:
        """
        Encrypt the given data as a base64-encoded string.

        :param value: The data to encrypt.
        :param purpose: Optional purpose for the encryption, used for key derivation.
        :param compress: Whether to compress the data before encryption.

        :return: The encrypted data as a base64-encoded string.
        """
        encryptor = self._factory.make(
            compress=compress, label=purpose.encode() if purpose else None
        )

        return encryptor.encrypt(value)

    def decrypt(self, value: str, *, purpose: str | None = None) -> str:
        """
        Decrypt the given base64-encoded string.

        :param value: The data to decrypt.
        :param purpose: Optional purpose for the decryption, used for key derivation.

        :return: The decrypted data as a string.
        """
        encryptor = self._factory.make(
            compress=True, label=purpose.encode() if purpose else None
        )

        return encryptor.decrypt(value)
