from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo
from expanse.schematic.support.doc_string.parsers.parser import DocStringParser


class PlainDocStringParser(DocStringParser):
    @classmethod
    def can_handle(cls, doc_string: str) -> bool:
        return True

    @classmethod
    def parse(cls, doc_string: str) -> DocStringInfo:
        info = DocStringInfo()
        lines = doc_string.strip().split("\n")

        if lines:
            info.summary = lines[0].strip()
            info.description = "\n".join(line.strip() for line in lines[1:]).strip()

        return info
