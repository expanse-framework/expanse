from typing import Any
from typing import Protocol

from expanse.http.responses.response import Response


class Adapter[T](Protocol):
    """
    An adapter is used to annotate a response and control its serialization.
    """

    def adapt(
        self, annotated: type[T], value: T, *args: Any, **kwargs: Any
    ) -> Response:
        """
        Apply the variant to the given value.
        """
        ...


class AsyncAdapter[T](Protocol):
    """
    An adapter is used to annotate a response and control its serialization.
    """

    async def adapt(
        self, annotated: type[T], value: T, *args: Any, **kwargs: Any
    ) -> Response:
        """
        Apply the variant to the given data.
        """
        ...
