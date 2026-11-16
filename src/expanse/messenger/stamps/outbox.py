from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutboxStamp:
    """
    A stamp that indicates that the message went through the outbox.
    """

    # The name of the transport the message must be relayed to.
    target_transport_name: str
