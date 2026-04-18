class UnconfiguredConnectionError(Exception):
    """
    Exception raised when a Redis connection is not configured.
    """


class MissingRedisPackageError(Exception):
    """
    Exception raised when the required Redis package is not installed.
    """
