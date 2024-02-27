from abc import ABC
from abc import abstractmethod

from cleo.io.outputs.output import Output

from expanse.http.request import Request
from expanse.http.response import Response


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
