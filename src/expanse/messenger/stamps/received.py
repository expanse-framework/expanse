from dataclasses import dataclass


@dataclass(frozen=True)
class ReceivedStamp:
    """
    A stamp used to mark messages as received, i.e. retrieved from the message broker by a transport.
    """
