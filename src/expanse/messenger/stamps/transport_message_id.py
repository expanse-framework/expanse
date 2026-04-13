from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransportMessageIdStamp[T]:
    """
    Stamp containing the unique identifier of a message in a transport.
    """

    id: T
