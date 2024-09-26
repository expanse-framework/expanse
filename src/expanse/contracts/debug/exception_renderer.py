from abc import ABC
from abc import abstractmethod


class ExceptionRenderer(ABC):
    @abstractmethod
    async def render(self, exception: Exception) -> str:
        """
        Render a given exception as HTML
        """
        ...
