from abc import ABC
from abc import abstractmethod

from expanse.http.request import Request


class ExceptionRenderer(ABC):
    @abstractmethod
    async def render(self, exception: Exception, request: Request) -> str:
        """
        Render a given exception as HTML
        """
        ...
