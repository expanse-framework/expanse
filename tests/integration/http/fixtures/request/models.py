from __future__ import annotations

import msgspec

from pydantic import BaseModel


class FooModel(BaseModel):
    bar: int


class FooStruct(msgspec.Struct):
    bar: int
