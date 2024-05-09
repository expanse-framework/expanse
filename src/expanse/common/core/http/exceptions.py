from http import HTTPStatus


class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        headers: dict | None = None,
    ) -> None:
        if detail is None:
            detail = HTTPStatus(status_code).phrase

        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"
