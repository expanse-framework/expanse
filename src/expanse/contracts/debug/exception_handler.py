from abc import ABC
from abc import abstractmethod
from collections.abc import Generator
from contextlib import contextmanager

from cleo.io.outputs.output import Output

from expanse.http.request import Request
from expanse.http.response import Response


class ExceptionHandler(ABC):
    @abstractmethod
    def report(self, e: Exception) -> None:
        """
        Report or log an exception.

        :param e: The exception to report or log

        :raises Exception
        """

    @abstractmethod
    def should_report(self, e: Exception) -> bool:
        """
        Determine whether the exception should be reported or not.

        :param e: The exception to verify
        """
        ...

    @abstractmethod
    def render(self, request: Request, e: Exception) -> Response:
        """
        Render the exception into an HTTP response.

        :param request: The request during which the exception was raised
        :param e: The exception to render
        """
        ...

    @abstractmethod
    def render_for_console(self, output: Output, e: Exception) -> None:
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
    ) -> Generator[None]:
        """
        Temporarily enable/disable raising unhandled exceptions.
        This is mainly useful for debugging purposes.

        :param raise_exceptions: Whether unhandled exceptions should be raised.
        """
        ...
