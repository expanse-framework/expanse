from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UniqueLockAcquiredStamp:
    """
    Stamp added to the envelope returned by a dispatch to notify
    that the unique lock of the message was acquired by this dispatch.
    """
