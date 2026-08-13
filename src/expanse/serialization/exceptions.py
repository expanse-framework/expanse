class SerializationError(Exception): ...


class UnconfiguredSerializerError(SerializationError): ...


class UnserializableObjectError(SerializationError): ...


class UnauthorizedTypeDecodingError(SerializationError):
    """
    Raised when an object of a disallowed type is attempted to be decoded.
    """
