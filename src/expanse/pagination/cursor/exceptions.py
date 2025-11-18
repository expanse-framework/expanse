from expanse.pagination.exceptions import PaginationError


class CursorException(PaginationError): ...


class InvalidCursorParameter(CursorException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Unable to find parameter [{name}] in pagination item.")
