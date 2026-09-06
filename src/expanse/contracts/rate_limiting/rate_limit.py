from dataclasses import dataclass

import whenever


@dataclass(frozen=True, slots=True)
class RateLimit:
    available_tokens: int
    retry_after: whenever.Instant
    accepted: bool
    limit: int
