from abc import ABC
from abc import abstractmethod

from expanse.schematic.support.doc_string.doc_string_info import DocStringInfo


class DocStringParser(ABC):
    @classmethod
    @abstractmethod
    def can_handle(cls, doc_string: str) -> bool: ...

    @classmethod
    @abstractmethod
    def parse(cls, doc_string: str) -> DocStringInfo: ...
