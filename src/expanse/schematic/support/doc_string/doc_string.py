from typing import ClassVar

from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo
from expanse.schematic.support.doc_string.parsers.google import GoogleDocStringParser
from expanse.schematic.support.doc_string.parsers.parser import DocStringParser
from expanse.schematic.support.doc_string.parsers.plain import PlainDocStringParser
from expanse.schematic.support.doc_string.parsers.sphinx import SphinxDocStringParser


class DocString:
    _parsers: ClassVar[list[type[DocStringParser]]] = [
        SphinxDocStringParser,
        GoogleDocStringParser,
    ]

    @classmethod
    def parse(cls, doc_string: str) -> DocStringInfo:
        for parser in cls._parsers:
            if parser.can_handle(doc_string):
                return parser.parse(doc_string)

        return PlainDocStringParser.parse(doc_string)
