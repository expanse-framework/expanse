class LogChannelConfigurationError(Exception):
    """
    Exception raised when there is an error in the log channel configuration.
    """


class UnconfiguredLogChannelError(LogChannelConfigurationError):
    """
    Exception raised when trying to create a log channel that hasn't been configured.
    """


class UnsupportedLogChannelDriverError(LogChannelConfigurationError):
    """
    Exception raised when trying to create a log channel with an unsupported driver.
    """
