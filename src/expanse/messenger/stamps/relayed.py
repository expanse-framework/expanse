from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelayedStamp:
    """
    A stamp that indicates that a received message has been relayed
    to its target transport instead of being handled.
    """

    # The name of the transport the message has been relayed to.
    target_transport_name: str
