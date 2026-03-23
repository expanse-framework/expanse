from typing import Annotated

from pydantic import Field
from pydantic import RootModel

from expanse.messenger.retry.multiplier.config import MultiplierRetryStrategyConfig


class RetryStrategyConfig(RootModel[MultiplierRetryStrategyConfig]):
    root: Annotated[MultiplierRetryStrategyConfig, Field(discriminator="type")]
