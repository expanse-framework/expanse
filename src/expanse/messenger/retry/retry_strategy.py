from abc import ABC
from abc import abstractmethod

from expanse.messenger.envelope import Envelope


class RetryStrategy(ABC):
    @abstractmethod
    def should_retry(
        self, envelope: Envelope, exception: Exception | None = None
    ) -> bool:
        """
        Determine whether the message should be retried based on the given envelope and exception.

        :param envelope: The envelope of the message that failed to be handled.
        :param exception: The exception that was raised during message handling.

        :return: True if the message should be retried, False otherwise.
        """
        ...

    @abstractmethod
    def retry_delay(
        self, envelope: Envelope, exception: Exception | None = None
    ) -> int:
        """
        Determine the delay before retrying the message based on the given envelope and exception.

        :param envelope: The envelope of the message that failed to be handled.
        :param exception: The exception that was raised during message handling.

        :return: The delay in seconds before retrying the message.
        """
        ...
