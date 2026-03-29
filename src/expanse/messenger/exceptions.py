class SerializerError(Exception):
    """
    Raised when a message cannot be serialized or deserialized.
    """


class NoSerializerRegisteredError(SerializerError):
    """
    Raised when no serializer is registered for a message type.
    """


class MessageEncodingFailedError(SerializerError):
    """
    Raised when a message cannot be encoded.
    """


class MessageDecodingFailedError(SerializerError):
    """
    Raised when a message cannot be decoded.
    """


class UnrecoverableMessageHandlingError(Exception):
    """
    Raised to notify the worker that a message handling error is unrecoverable.
    In practice, this means that the message should not be retried
    and should be discarded or moved to the failure transport.
    """


class InvalidHandlerError(Exception):
    """
    Raised when a handler is invalid, for example if it does not have the correct signature.
    """


class NoDefaultTransportError(Exception):
    """
    Raised when no default transport is configured and no transport name is provided.
    """


class SelfHandlingMessageWithNoHandlerError(Exception):
    """
    Raised when a message marked with SelfHandlingStamp does not have a callable 'handle' method.
    """
