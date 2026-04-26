from expanse.messenger.envelope import Envelope


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


class SelfHandlingMessageWithNoHandlerError(UnrecoverableMessageHandlingError):
    """
    Raised when a message marked with SelfHandlingStamp does not have a callable 'handle' method.
    """


class UnconfiguredTransportError(Exception):
    """
    Raised when a transport is requested that is not configured.
    """


class UnsupportedTransportDriverError(Exception):
    """
    Raised when a transport is configured with an unsupported driver.
    """


class UnconfiguredRetryStrategyError(Exception):
    """
    Raised when a retry strategy is requested that is not configured.
    """


class UnsupportedRetryStrategyError(Exception):
    """
    Raised when a retry strategy is configured with an unsupported type.
    """


class MessageHandlingFailedError(Exception):
    """
    Raised when a message handling fails with one or more exceptions.

    The exceptions can be retrieved from the `errors` attribute, which is a dictionary mapping handler identifiers to exceptions.
    """

    def __init__(self, envelope: Envelope, errors: dict[str, Exception]) -> None:
        self.envelope: Envelope = envelope
        self.errors: dict[str, Exception] = errors

        first_failed_handler, first_exception = next(iter(errors.items()))
        error_message = [
            f"Message handling failed for message {envelope.open.__class__}: "
        ]

        if len(errors) == 1:
            error_message.append(str(first_exception))
        else:
            error_message.append(
                f"{len(errors)} handlers failed. First failed handler: {first_failed_handler} with exception: {first_exception}"
            )

        super().__init__("".join(error_message))


class TransportError(Exception):
    """
    Raised when a transport encounters an error while sending or receiving a message.
    """


class MessageBusError(Exception): ...


class TransactionalMessageBusError(MessageBusError): ...
