from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Generator
from contextlib import contextmanager
from typing import Self
from typing import TypeVar

from cleo.io.outputs.output import Output

from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response


_TError = TypeVar("_TError", bound=Exception)


class ExceptionHandler(ABC):
    @abstractmethod
    async def report(self, e: Exception) -> None:
        """
        Report or log an exception.

        :param e: The exception to report or log

        :raises Exception
        """

    @abstractmethod
    async def should_report(self, e: Exception) -> bool:
        """
        Determine whether the exception should be reported or not.

        :param e: The exception to verify
        """
        ...

    @abstractmethod
    def ignore(self, exception_class: type[Exception]) -> Self:
        """
        Ignore a specific exception class when reporting exceptions.

        :param exception_class: The exception class to ignore.
        """
        ...

    @abstractmethod
    async def render(self, request: Request, e: Exception) -> Response:
        """
        Render the exception into an HTTP response.

        :param request: The request during which the exception was raised
        :param e: The exception to render
        """
        ...

    @abstractmethod
    async def render_for_console(self, output: Output, e: Exception) -> None:
        """
        Render the exception to the console output.

        :param output: the output to render the exception to
        :param e: The exception to render
        """
        ...

    @abstractmethod
    @contextmanager
    def raise_unhandled_exceptions(
        self, raise_exceptions: bool = True
    ) -> Generator[None, None, None]:
        """
        Temporarily enable/disable raising unhandled exceptions.
        This is mainly useful for debugging purposes.

        :param raise_exceptions: Whether unhandled exceptions should be raised.
        """
        ...

    @abstractmethod
    def prepare_using(
        self, exception_class: type[_TError], preparer: Callable[[_TError], Exception]
    ) -> None:
        """
        Register a preparer for a specific exception class.

        :param exception_class: The exception class to prepare, i.e. convert to another exception.
        :param preparer: The preparer function to use to convert the given exception type.
        """
        ...
