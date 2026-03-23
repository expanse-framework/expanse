from dataclasses import dataclass


@dataclass(frozen=True)
class DelayStamp:
    """
    A stamp used to mark messages with a delay, i.e. to be processed after a certain period.
    """

    # The delay in milliseconds before the message should be processed.
    delay: int
