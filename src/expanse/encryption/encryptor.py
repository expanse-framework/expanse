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
from expanse.encryption.utils import generate_random_string
from expanse.support.secret import Secret


class Cipher(Enum):
    AES_256_GCM = "aes-256-gcm"


class Encryptor(EncryptorContract):
    CIPHERS: ClassVar[dict[Cipher, type[BaseCipher]]] = {
        Cipher.AES_256_GCM: AES256GCMCipher
    }

    def __init__(
        self,
        key_chain: KeyChain,
        cipher: Cipher = Cipher.AES_256_GCM,
        *,
        salt: Secret[bytes] | bytes | None = None,
        purpose: bytes | None = None,
        compress: bool = True,
        store_key_references: bool = False,
    ) -> None:
        self._key_chain = key_chain
        self._secret_key = key_chain.latest
        self._cipher = cipher
        self._compress = compress
        self._compressor = ZlibCompressor()
        self._salt: Secret[bytes] | None = (
            Secret[bytes].wrap(salt) if salt is not None else None
        )
        self._purpose: bytes | None = purpose
        self._purpose = purpose
        self._store_key_references: bool = store_key_references

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

        key = KeyGenerator.generate_key(
            self._secret_key,
            key_size=cipher_class.key_length,
            salt=self._salt,
            purpose=self._purpose,
        )

        cipher = cipher_class(key.value)

        encoded: bytes = value.encode()
        if self._compress:
            encoded = self._compressor.compress(encoded)

        encrypted = cipher.encrypt(
            encoded,
            additional_data=self._build_additional_data(kid=self._secret_key.id),
        )
        if self._compress:
            encrypted.headers["z"] = 1

        if self._store_key_references:
            encrypted.headers["k"] = self._secret_key.id

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

        if kid := message.headers.get("k"):
            key = self._key_chain.find(kid.decode())

            if key is None:
                raise DecryptionError(f"Key with id '{kid}' not found in key chain")

            return self._decrypt(
                message,
                key,
                additional_data=self._build_additional_data(
                    compress=bool(message.headers.get("z")),
                    kid=kid.decode(),
                ),
            )

        additional_data = self._build_additional_data(
            compress=bool(message.headers.get("z"))
        )
        for key in self._key_chain:
            try:
                return self._decrypt(
                    message,
                    key,
                    additional_data=additional_data,
                )
            except DecryptionError:
                continue

        raise DecryptionError("Unable to decrypt message")

    def _decrypt(
        self, message: Message, key: Key, additional_data: bytes | None
    ) -> str:
        cipher_class = self.CIPHERS[self._cipher]

        key = KeyGenerator.generate_key(
            key,
            key_size=cipher_class.key_length,
            salt=self._salt,
            purpose=self._purpose,
        )

        cipher = cipher_class(key.value)

        decrypted = cipher.decrypt(message, additional_data=additional_data)

        if message.headers.get("z"):
            decrypted = self._compressor.decompress(decrypted)

        return decrypted.decode()

    def _build_additional_data(
        self, compress: bool | None = None, kid: str | None = None
    ) -> bytes:
        if compress is None:
            compress = self._compress

        additional_data: list[bytes] = [b"1" if compress else b"0"]

        if self._store_key_references and kid is not None:
            additional_data.append(kid.encode())

        if self._purpose:
            additional_data.append(self._purpose)

        return b"\x00".join(additional_data)

    @classmethod
    def generate_random_key(cls, cipher: Cipher = Cipher.AES_256_GCM) -> str:
        cipher_class = cls.CIPHERS[cipher]

        return generate_random_string(cipher_class.key_length)
