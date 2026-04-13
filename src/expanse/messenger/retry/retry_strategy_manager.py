from typing import Any

from expanse.configuration.config import Config
from expanse.messenger.exceptions import UnconfiguredRetryStrategyError
from expanse.messenger.exceptions import UnsupportedRetryStrategyError
from expanse.messenger.retry.retry_strategy import RetryStrategy


class RetryStrategyManager:
    def __init__(self, config: Config) -> None:
        self._config: Config = config
        self._strategies: dict[str, RetryStrategy] = {}

    def strategy(self, name: str) -> RetryStrategy:
        if name in self._strategies:
            return self._strategies[name]

        strategy_configs: dict[str, dict[str, Any]] = self._config.get(
            "messenger.retry_strategies", {}
        )

        if name not in strategy_configs:
            raise UnconfiguredRetryStrategyError(
                f"Retry strategy '{name}' is not configured."
            )

        strategy_config = strategy_configs[name]
        strategy_type = strategy_config.get("type")
        if strategy_type is None:
            raise UnconfiguredRetryStrategyError(
                f"Retry strategy '{name}' is missing a type."
            )

        match strategy_type:
            case "multiplier":
                from expanse.messenger.retry.multiplier.config import (
                    MultiplierRetryStrategyConfig,
                )
                from expanse.messenger.retry.multiplier.multiplier_retry_strategy import (
                    MultiplierRetryStrategy,
                )

                strategy = MultiplierRetryStrategy(
                    MultiplierRetryStrategyConfig.model_validate(strategy_config)
                )
                self._strategies[name] = strategy
                return strategy
            case _:
                raise UnsupportedRetryStrategyError(
                    f"Retry strategy type '{strategy_type}' is not supported."
                )
