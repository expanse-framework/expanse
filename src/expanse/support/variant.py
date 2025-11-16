from typing import Any
from typing import Protocol

from expanse.http.responses.response import Response


class Variant[T](Protocol):
    """
    A variant is used to annotate a response and control its serialization.
    """

    def apply(
        self, annotated: type[T], value: T, *args: Any, **kwargs: Any
    ) -> Response:
        """
        Apply the variant to the given value.
        """
        ...


class AsyncVariant[T](Protocol):
    """
    A variant is used to annotate a response and control its serialization.
    """

    async def apply(
        self, annotated: type[T], value: T, *args: Any, **kwargs: Any
    ) -> Response:
        """
        Apply the variant to the given data.
        """
        ...
