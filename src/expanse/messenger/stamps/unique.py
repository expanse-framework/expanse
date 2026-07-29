from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UniqueStamp:
    """
    Stamp used to notify that only one message
    of a particular type should be processed at the same time.
    """
