from expanse.core.http.exceptions import HTTPException


class CookieError(Exception): ...


class HeaderError(Exception): ...


class InvalidForwardedHeaderError(HeaderError): ...


class ConflictingForwardedHeadersError(HeaderError): ...


class SuspiciousOperationError(Exception): ...


class ClientDisconnectedError(Exception): ...


class MalformedJSONError(HTTPException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(status_code=400, detail=message or "Malformed JSON")


class UnsupportedContentTypeError(HTTPException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(status_code=415, detail=message or "Unsupported Content Type")


class MalformedMultipartError(HTTPException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(status_code=400, detail=message or "Malformed Multipart Data")


class NoUploadFileFoundError(HTTPException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            status_code=400, detail=message or "No upload file found in the request"
        )
