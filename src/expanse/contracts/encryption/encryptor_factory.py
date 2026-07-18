from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from expanse.contracts.encryption.encryptor import Encryptor


class EncryptorFactory(ABC):
    @abstractmethod
    def make(self, compress: bool = True, purpose: bytes | None = None) -> "Encryptor":
        """
        Create an instance of an Encryptor.

        :param compress: Whether to compress the data before encryption.
        :param purpose: Optional purpose for the encryption, used for key derivation.

        :return: An instance of an Encryptor.
        """
        ...
