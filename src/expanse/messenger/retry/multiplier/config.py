from typing import Literal

from pydantic_settings import BaseSettings


class MultiplierRetryStrategyConfig(BaseSettings):
    type: Literal["multiplier"] = "multiplier"

    # Maximum number of times a message will be retried
    max_retries: int = 3
    # Time to wait before the first retry (in milliseconds)
    delay: int = 1000
    # Maximum delay between retries (in milliseconds)
    max_delay: int | None = None
    # Multiplier applied to the delay on each subsequent retry
    multiplier: int = 2
    # Randomness factor (between 0 and 1.0) added to each delay to
    # prevent a thundering herd effect upon multiple messages being retried
    jitter: float = 0.1
