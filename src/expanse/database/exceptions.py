class DatabaseConfigurationError(Exception):
    """
    Raised when there is an error in the database configuration.
    """


class UnconfiguredDatabaseError(DatabaseConfigurationError):
    """
    Raised when a requested database is not configured.
    """


class UnconfiguredDatabaseDriverError(DatabaseConfigurationError):
    """
    Raised when a database is configured without a driver.
    """


class UnsupportedDatabaseDriverError(DatabaseConfigurationError):
    """
    Raised when a database is configured with an unsupported driver.
    """
