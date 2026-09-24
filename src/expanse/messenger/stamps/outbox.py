from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutboxStamp:
    """
    A stamp that indicates that the message went through the outbox.
    """

    target_transport_name: str | None = None
