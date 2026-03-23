import random

from expanse.messenger.envelope import Envelope
from expanse.messenger.retry.multiplier.config import MultiplierRetryStrategyConfig
from expanse.messenger.retry.retry_strategy import RetryStrategy
from expanse.messenger.stamps.redelivery import RedeliveryStamp


class MultiplierRetryStrategy(RetryStrategy):
    """
    A retry strategy that multiplies the delay between retries by a given factor.
    The delay is calculated as follows: delay = base_delay * (multiplier ** retry_count)
    """

    def __init__(self, config: MultiplierRetryStrategyConfig) -> None:
        self._config: MultiplierRetryStrategyConfig = config

    def should_retry(
        self, envelope: Envelope, exception: Exception | None = None
    ) -> bool:
        redelivery_stamp = envelope.stamp(RedeliveryStamp)

        if redelivery_stamp is None:
            # If the message has never been retried before, we should retry it.
            return True

        return redelivery_stamp.retry_count < self._config.max_retries

    def retry_delay(
        self, envelope: Envelope, exception: Exception | None = None
    ) -> int:
        redelivery_stamp = envelope.stamp(RedeliveryStamp)

        if redelivery_stamp is None:
            # If the message has never been retried before, we return the base delay.
            return self._config.delay

        # We calculate the delay based on the number of retries and the multiplier.
        delay: int = self._config.delay * (
            self._config.multiplier**redelivery_stamp.retry_count
        )

        # We add some randomness to the delay to prevent a thundering herd effect
        # upon multiple messages being retried at the same time.
        jitter = int(delay * self._config.jitter)
        delay += random.randint(-jitter, jitter)

        return delay
