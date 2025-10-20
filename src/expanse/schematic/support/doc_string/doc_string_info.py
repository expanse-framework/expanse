from dataclasses import dataclass
from dataclasses import field


@dataclass
class ParameterDoc:
    """Documentation for a single parameter."""

    name: str
    description: str
    type_hint: str | None = None


@dataclass
class RaisesDoc:
    """Documentation for an exception that can be raised."""

    exception: str
    description: str
    status_code: int


@dataclass
class DocStringInfo:
    """Parsed information from a docstring."""

    summary: str = ""
    description: str = ""
    parameters: dict[str, ParameterDoc] = field(default_factory=dict)
    returns: str = ""
    return_type: str | None = None
    raises: list[RaisesDoc] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
