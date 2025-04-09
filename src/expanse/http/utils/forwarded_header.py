import re
import string

from collections.abc import Sequence
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import IPv6Address
from ipaddress import ip_address
from re import Pattern
from typing import Final
from typing import NotRequired
from typing import Self
from typing import TypedDict

from expanse.http.exceptions import InvalidForwardedHeaderError


_TCHAR: Final[str] = string.digits + string.ascii_letters + r"!#$%&'*+.^_`|~-"
# '-' at the end to prevent interpretation as range in a char class

_TOKEN: Final[str] = rf"[{_TCHAR}]+"

_QDTEXT: Final[str] = r"[{}]".format(
    r"".join(chr(c) for c in (9, 32, 33, *tuple(range(35, 127))))
)
# qdtext includes 0x5C to escape 0x5D ('\]')
# qdtext excludes obs-text (because obsoleted, and encoding not specified)

_QUOTED_PAIR: Final[str] = r"\\[\t !-~]"

_QUOTED_STRING: Final[str] = rf'"(?:{_QUOTED_PAIR}|{_QDTEXT})*"'

_FORWARDED_PAIR: Final[str] = (
    rf"({_TOKEN})=({_TOKEN}|{_QUOTED_STRING})(?::(\d{{1,4}}))?"
)

_QUOTED_PAIR_REPLACE_RE: Final[Pattern[str]] = re.compile(r"\\([\t !-~])")
# same pattern as _QUOTED_PAIR but contains a capture group

_FORWARDED_PAIR_RE: Final[Pattern[str]] = re.compile(_FORWARDED_PAIR)

_ENCLOSED_IPV6_RE: Final[Pattern[str]] = re.compile(r"\[([^]]+)\](?::(\d{1,4}))?")


@dataclass(frozen=True, slots=True)
class Node:
    ip: IPv4Address | IPv6Address | None
    port: int | None


class Nodes(TypedDict):
    by: NotRequired[list[Node]]
    for_: NotRequired[list[Node]]
    host: NotRequired[str]
    proto: NotRequired[str]


@dataclass(frozen=True, slots=True)
class ForwardedHeader:
    """
    Represents a parsed Forwarded header.
    """

    by: list[Node] | None = None
    for_: list[Node] | None = None
    host: str | None = None
    proto: str | None = None

    @classmethod
    def parse(cls, header: str | Sequence[str]) -> Self:
        """
        Parses a Forwarded header string and returns a ForwardedHeader object.
        """
        if isinstance(header, str):
            header = [header]

        elems: Nodes = {}
        for field_value in header:
            length = len(field_value)
            pos = 0
            need_separator = False
            while 0 <= pos < length:
                match = _FORWARDED_PAIR_RE.match(field_value, pos)
                if match is not None:  # got a valid forwarded-pair
                    if need_separator:
                        # bad syntax here, skip to next comma
                        pos = field_value.find(",", pos)
                    else:
                        name, value, port = match.groups()
                        if value[0] == '"':
                            # quoted string: remove quotes and unescape
                            value = _QUOTED_PAIR_REPLACE_RE.sub(r"\1", value[1:-1])

                        if value[0] == "[" and (m := _ENCLOSED_IPV6_RE.match(value)):
                            # IPv6 address: remove brackets
                            value, port = m.groups()

                        name = name.lower()
                        if name == "for":
                            # for is a reserved word in Python, so we use for_ instead
                            name = "for_"

                        match name:
                            case "by" | "for_":
                                if name not in elems:
                                    elems[name] = []

                                elems[name].append(
                                    Node(ip_address(value), int(port) if port else None)
                                )
                            case "host":
                                elems[name] = value + (f":{port}" if port else "")
                            case "proto":
                                elems[name] = value.lower()
                            case _:
                                raise InvalidForwardedHeaderError(
                                    f'Invalid directive "{name}" found in the Forwarded header'
                                )

                        pos += len(match.group(0))
                        need_separator = True
                elif (
                    field_value[pos] == "," or field_value[pos] == ";"
                ):  # next forwarded-element
                    need_separator = False
                    pos += 1
                elif field_value[pos] in " \t":
                    # Allow whitespace even between forwarded-pairs, though
                    # RFC 7239 doesn't. This simplifies code and is in line
                    # with Postel's law.
                    pos += 1
                else:
                    # bad syntax here, skip to next comma
                    pos = field_value.find(",", pos)

        return cls(**elems)
