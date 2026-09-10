from pydantic import BaseModel

from expanse.support.duration import SingleUnitDuration


class SlidingWindowRateLimiterConfig(BaseModel):
    limit: int
    interval: SingleUnitDuration
    cache_store: str | None = None
