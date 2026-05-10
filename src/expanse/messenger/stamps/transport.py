from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransportStamp:
    """
    Stamp used to route a message to a specific transport.
    """

    name: str
