from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated
from typing import Self
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)

if TYPE_CHECKING:
    from typing import Union

    Query = Union[T, T]  # noqa: UP007
else:

    class Query:
        def __class_getitem__(cls, item: type[T]) -> Annotated[type[T], type[Self]]:
            return Annotated[item, cls]
