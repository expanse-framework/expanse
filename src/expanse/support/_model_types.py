from __future__ import annotations

import re

from typing import Any
from typing import TypeGuard

import msgspec

from pydantic import BaseModel


def is_pydantic_model(annotation: Any) -> TypeGuard[type[BaseModel]]:
    try:
        return isinstance(annotation, type) and issubclass(annotation, BaseModel)
    except TypeError:
        return False


def is_msgspec_struct(annotation: Any) -> TypeGuard[type[msgspec.Struct]]:
    try:
        return isinstance(annotation, type) and issubclass(annotation, msgspec.Struct)
    except TypeError:
        return False


def parse_msgspec_validation_error(
    error: msgspec.ValidationError,
) -> tuple[str, list[str | int]]:
    """
    Best-effort split of a msgspec validation error message into a human
    readable message and a location path, e.g. "Expected `int`, got `str` -
    at `$.age`" -> ("Expected `int`, got `str`", ["age"]).

    Unlike Pydantic, msgspec fails fast on the first error and does not
    expose a structured location, so this is derived from the trailing
    `` - at `$...` `` suffix of the error message, when present.
    """
    message = str(error)
    marker = " - at `$"
    if marker not in message:
        return message, []

    message, raw_path = message.rsplit(marker, 1)
    raw_path = raw_path.rstrip("`")

    loc: list[str | int] = [
        int(part) if part.isdigit() else part
        for part in re.split(r"\.|\[|\]", raw_path)
        if part
    ]

    return message, loc
