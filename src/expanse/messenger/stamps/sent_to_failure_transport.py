from dataclasses import dataclass


@dataclass(frozen=True)
class SentToFailureTransportStamp:
    original_transport: str
