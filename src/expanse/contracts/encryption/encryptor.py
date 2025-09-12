from abc import ABC
from abc import abstractmethod

from expanse.encryption.message import Message


class Encryptor(ABC):
    @abstractmethod
    def encrypt(self, value: str) -> str:
        """
        Encrypt the given data.
        """
        ...

    @abstractmethod
    def encrypt_raw(self, value: str) -> Message:
        """
        Encrypt the given data, optionally in a deterministic way.

        The result of the encryption will be a Message object containing the encrypted
        data and any additional headers needed to decrypt it. Additional headers can be added
        to the message if necessary.
        """
        ...

    @abstractmethod
    def decrypt(self, message: Message | str) -> str:
        """
        Decrypt the given message.
        """
        ...
