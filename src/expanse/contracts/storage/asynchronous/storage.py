from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncIterator
from collections.abc import Buffer
from collections.abc import Iterable
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import IO


class Storage(ABC):
    @abstractmethod
    async def get(self, path: str) -> bytes:
        """
        Rerieve the content of a file.

        :param path: The path to the file to retrieve.

        :return: The content of the file, or None if the file does not exist.
        """

    @abstractmethod
    async def stream(
        self, path: str, chunk_size: int = 10 * 1024 * 1024
    ) -> AsyncIterator[bytes]:
        """
        Retrieve the content of a file as a stream.

        :param path: The path to the file to stream.
        :param chunk_size: The size of the chunks to read from the file. Defaults to 10MB.

        :return: An asynchronous iterator that yields the content of the file in chunks.
        """

    @abstractmethod
    async def put(
        self,
        path: str,
        content: (
            IO[bytes] | Path | bytes | Buffer | Iterator[Buffer] | Iterable[Buffer]
        ),
    ) -> None:
        """
        Store a file.

        :param path: The path to the file to store.
        :param content: The content of the file to store.

        :return: True if the file was stored successfully, False otherwise.
        """

    @abstractmethod
    async def delete(self, path: str) -> None:
        """
        Delete a file.

        :param path: The path to the file to delete.

        :return: True if the file was deleted successfully, False otherwise.
        """

    @abstractmethod
    async def copy(self, source: str, destination: str) -> None:
        """
        Copy a file from one path to another.

        :param source: The path to the file to copy.
        :param destination: The path to copy the file to.

        :return: True if the file was copied successfully, False otherwise.
        """

    @abstractmethod
    async def move(self, source: str, destination: str) -> None:
        """
        Move a file from one path to another.

        :param source: The path to the file to move.
        :param destination: The path to move the file to.

        :return: True if the file was moved successfully, False otherwise.
        """

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        :param path: The path to the file to check.

        :return: True if the file exists, False otherwise.
        """

    @abstractmethod
    async def list(self, prefix: str = "") -> list[str]:
        """
        List the files in the storage.

        :param prefix: An optional prefix to filter the files by.

        :return: A list of file paths that match the given prefix.
        """

    @abstractmethod
    async def size(self, path: str) -> int:
        """
        Get the size of a file in bytes.

        :param path: The path to the file to get the size of.

        :return: The size of the file in bytes.
        """

    @abstractmethod
    async def last_modified(self, path: str) -> datetime:
        """
        Get the last modified time of a file as a Unix timestamp.

        :param path: The path to the file to get the last modified time of.

        :return: The last modified time of the file as a Unix timestamp.
        """
