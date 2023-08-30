from __future__ import annotations

from pydantic import BaseModel


class FooModel(BaseModel):
    bar: int
