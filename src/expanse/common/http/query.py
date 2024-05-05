from __future__ import annotations

from typing import Generic
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class Query(BaseModel, Generic[T]):
    params: T
