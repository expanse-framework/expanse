import secrets

from enum import Enum
from typing import ClassVar

from expanse.contracts.encryption.encryptor import Encryptor as EncryptorContract
from expanse.encryption.ciphers.aes256_gcm import AES256GCMCipher
from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.compressors.zlib import ZlibCompressor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.key_generator import KeyGenerator
from expanse.encryption.message import Message


class Cipher(Enum):
    AES_256_GCM = "aes-256-gcm"


class Encryptor(EncryptorContract):
    CIPHERS: ClassVar[dict[Cipher, type[BaseCipher]]] = {
        Cipher.AES_256_GCM: AES256GCMCipher
    }

    def __init__(
        self,
        key_chain: KeyChain,
        key_generator: KeyGenerator,
        cipher: Cipher = Cipher.AES_256_GCM,
        *,
        compress: bool = True,
    ) -> None:
        self._key_chain = key_chain
        self._secret_key = key_chain.latest
        self._cipher = cipher
        self._compress = compress
        self._compressor = ZlibCompressor()
        self._key_generator = key_generator

    def has_compression(self) -> bool:
        return self._compress

    def encrypt(self, value: str) -> str:
        """
        Encrypt the given data as a base64-encoded string.

        Similar to `encrypt_raw`, but returns the Message as a base64-encoded string.

        :param value: The data to encrypt.
        """
        message = self.encrypt_raw(value)

        return message.encode()

    def encrypt_raw(self, value: str) -> Message:
        """
        Encrypt the given data.

        The result of the encryption will be a Message object containing the encrypted
        data and any additional headers needed to decrypt it. Additional headers can be added
        to the message if necessary.

        If key derivation is enabled, the key used to encrypt the data
        will be derived from the secret key using the configured key derivation salt.
        Otherwise, the secret key will be used directly.

        :param value: The data to encrypt.
        """
        cipher_class = self.CIPHERS[self._cipher]

        key = self._key_generator.generate_key(
            self._secret_key, key_size=cipher_class.key_length
        )

        cipher = cipher_class(key.value)

        encoded: bytes = value.encode()
        if self._compress:
            encoded = self._compressor.compress(encoded)

        encrypted = cipher.encrypt(encoded)
        if self._compress:
            encrypted.headers["z"] = 1

        return encrypted

    def decrypt(self, message: Message | str) -> str:
        """
        Decrypt the given message.

        The message can be provided as a Message object or as a base64-encoded string.

        To decrypt the message, the encryptor will try to use each key in the configured key chain
        until it finds the correct one. If none of the keys can decrypt the message, an exception
        will be raised.

        :param message: The message to decrypt.
        """
        if isinstance(message, str):
            message = Message.decode(message)

        for key in self._key_chain:
            try:
                return self._decrypt(message, key)
            except DecryptionError:
                continue

        raise DecryptionError("Unable to decrypt message")

    def _decrypt(self, message: Message, key: Key) -> str:
        cipher_class = self.CIPHERS[self._cipher]

        key = self._key_generator.generate_key(key, key_size=cipher_class.key_length)

        cipher = cipher_class(key.value)

        decrypted = cipher.decrypt(message)

        if message.headers.get("z"):
            decrypted = self._compressor.decompress(decrypted)

        return decrypted.decode()

    @classmethod
    def generate_random_key(cls, cipher: Cipher = Cipher.AES_256_GCM) -> bytes:
        cipher_class = cls.CIPHERS[cipher]
        key = secrets.token_bytes(cipher_class.key_length)

        return key
