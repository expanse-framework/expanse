class MissingSecretKeyError(RuntimeError):
    def __init__(self, message: str = "The application encryption key is not defined."):
        super().__init__(message)


class GenericEncryptionError(Exception): ...


class DecryptionError(GenericEncryptionError): ...


class MessageDecodeError(GenericEncryptionError): ...
