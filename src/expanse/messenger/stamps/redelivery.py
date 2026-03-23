from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RedeliveryStamp:
    """
    Stamp indicating that a message is being redelivered after a failure.
    """

    retry_count: int
    redelivered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
