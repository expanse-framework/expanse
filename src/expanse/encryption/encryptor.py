import secrets

from enum import Enum
from typing import ClassVar

from expanse.encryption.ciphers.aes256_gcm import AES256GCMCipher
from expanse.encryption.ciphers.base_cipher import BaseCipher
from expanse.encryption.compressors.zlib import ZlibCompressor
from expanse.encryption.errors import DecryptionError
from expanse.encryption.key import Key
from expanse.encryption.key_chain import KeyChain
from expanse.encryption.key_generator import KeyGenerator
from expanse.encryption.message import Message


class Cipher(Enum):
    AES_256_GCM: str = "aes-256-gcm"


class Encryptor:
    CIPHERS: ClassVar[dict[Cipher, type[BaseCipher]]] = {
        Cipher.AES_256_GCM: AES256GCMCipher
    }

    def __init__(
        self,
        key_chain: KeyChain,
        salt: bytes,
        cipher: Cipher = Cipher.AES_256_GCM,
        compress: bool = True,
        derive: bool = True,
    ) -> None:
        self._key_chain = key_chain
        self._secret_key = key_chain.latest
        self._salt = salt
        self._cipher = cipher
        self._compress = compress
        self._compressor = ZlibCompressor()
        self._derive = derive

    def has_compression(self) -> bool:
        return self._compress

    def has_derivation(self) -> bool:
        return self._derive

    def encrypt(self, data: str, deterministic: bool = False) -> Message:
        """
        Encrypt the given data, optionally in a deterministic way.

        The result of the encryption will be a Message object containing the encrypted
        data and any additional headers needed to decrypt it. Additional headers can be added
        to the message if necessary.

        If key derivation is enabled, the key used to encrypt the data
        will be derived from the secret key using the configured key derivation salt.
        Otherwise, the secret key will be used directly.

        When using deterministic encryption, the same input data will always produce
        the same encrypted output. This is useful when encrypting data that needs to be
        compared or indexed, for instance values in a database that need to be searchable.

        Note that you should always use non-deterministic encryption for sensitive data unless
        you have a specific reason to use deterministic encryption.

        @param data: The data to encrypt.
        @param deterministic: Whether to encrypt the data in a deterministic way.
        """
        cipher_class = self.CIPHERS[self._cipher]

        if self._derive:
            key = self.derive_key(self._secret_key, length=cipher_class.key_length)
        else:
            key = self._secret_key

        cipher = cipher_class(key.value, deterministic=deterministic)

        encoded: bytes = data.encode()
        if self._compress:
            encoded = self._compressor.compress(encoded)

        encrypted = cipher.encrypt(encoded)
        if self._compress:
            encrypted.headers["z"] = 1

        return encrypted

    def decrypt(self, message: Message) -> str:
        """
        Decrypt the given message.

        To decrypt the message, the encryptor will try to use each key in the configured key chain
        until it finds the correct one. If none of the keys can decrypt the message, an exception
        will be raised.

        @param message: The message to decrypt.
        """
        for key in self._key_chain:
            try:
                return self._decrypt(message, key)
            except DecryptionError:
                continue

        raise DecryptionError("Unable to decrypt message")

    def _decrypt(self, message: Message, key: Key) -> str:
        cipher_class = self.CIPHERS[self._cipher]

        if self._derive:
            key = self.derive_key(key, length=cipher_class.key_length)
        else:
            key = key

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

    def derive_key(
        self, key: Key, iterations: int | None = None, length: int = 32
    ) -> Key:
        return KeyGenerator(key, iterations=iterations).generate_key(
            self._salt, key_size=length
        )
