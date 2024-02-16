from __future__ import annotations

from typing import Generic
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class Form(BaseModel, Generic[T]):
    data: T
