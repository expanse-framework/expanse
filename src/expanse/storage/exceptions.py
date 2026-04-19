class StorageError(Exception):
    """
    Base class for all storage-related errors.
    """


class NoDefaultStorageError(StorageError):
    """
    Raised when no default storage is configured.
    """


class UnconfiguredStorageError(StorageError):
    """
    Raised when a storage that is not configured is requested.
    """


class UnsupportedStorageDriverError(StorageError):
    """
    Raised when a storage driver that is not supported is requested.
    """
