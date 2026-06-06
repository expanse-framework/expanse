class NoDefaultStoreError(Exception):
    """
    Raised when no default cache store is configured.
    """


class UnconfiguredStoreError(Exception):
    """
    Raised when a requested cache store is not configured.
    """


class UnsupportedStoreDriverError(Exception):
    """
    Raised when a cache store is configured with an unsupported driver.
    """


class UnconfiguredL1CacheBusError(Exception):
    """
    Raised when a cache store is configured with an L1 cache that is missing a bus configuration.
    """


class UnsupportedL1CacheBusDriverError(Exception):
    """
    Raised when a cache store is configured with an L1 cache that has an unsupported bus driver.
    """
