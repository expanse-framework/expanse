from __future__ import annotations

import pytest

from pydantic import ValidationError

from expanse.redis.config.redis import BackoffConfig
from expanse.redis.config.redis import ConstantBackoffConfig
from expanse.redis.config.redis import GenericBackoffConfig
from expanse.redis.config.redis import RedisConfig


def test_redis_config_minimal() -> None:
    config = RedisConfig.model_validate({"url": "redis://localhost:6379/0"})

    assert str(config.url) == "redis://localhost:6379/0"
    assert config.max_retries == 3
    assert config.backoff is not None


def test_redis_config_custom_max_retries() -> None:
    config = RedisConfig.model_validate(
        {"url": "redis://localhost:6379/0", "max_retries": 5}
    )

    assert config.max_retries == 5


def test_redis_config_no_backoff() -> None:
    config = RedisConfig.model_validate(
        {"url": "redis://localhost:6379/0", "backoff": None}
    )

    assert config.backoff is None


def test_redis_config_invalid_url_raises_error() -> None:
    with pytest.raises(ValidationError):
        RedisConfig.model_validate({"url": "not-a-url"})


def test_redis_config_rediss_url() -> None:
    config = RedisConfig.model_validate({"url": "rediss://localhost:6380/0"})

    assert str(config.url) == "rediss://localhost:6380/0"


def test_constant_backoff_config_defaults() -> None:
    config = ConstantBackoffConfig.model_validate({})

    assert config.strategy == "constant"
    assert config.backoff == 1


def test_constant_backoff_config_custom_backoff() -> None:
    config = ConstantBackoffConfig.model_validate({"backoff": 5})

    assert config.backoff == 5


def test_generic_backoff_config_defaults() -> None:
    config = GenericBackoffConfig.model_validate({})

    assert config.strategy == "decorrelated_jitter"
    assert config.base == 1
    assert config.cap == 10


def test_generic_backoff_config_custom_values() -> None:
    config = GenericBackoffConfig.model_validate(
        {"strategy": "exponential", "base": 2, "cap": 20}
    )

    assert config.strategy == "exponential"
    assert config.base == 2
    assert config.cap == 20


@pytest.mark.parametrize(
    "strategy",
    [
        "exponential",
        "full_jitter",
        "equal_jitter",
        "decorrelated_jitter",
        "exponential_with_jitter",
    ],
)
def test_generic_backoff_config_valid_strategies(strategy: str) -> None:
    config = GenericBackoffConfig.model_validate({"strategy": strategy})

    assert config.strategy == strategy


def test_generic_backoff_config_invalid_strategy_raises_error() -> None:
    with pytest.raises(ValidationError):
        GenericBackoffConfig.model_validate({"strategy": "invalid"})


def test_backoff_config_constant_discriminator() -> None:
    config = BackoffConfig.model_validate({"strategy": "constant", "backoff": 3})

    assert isinstance(config.root, ConstantBackoffConfig)
    assert config.root.backoff == 3


def test_backoff_config_generic_discriminator() -> None:
    config = BackoffConfig.model_validate(
        {"strategy": "exponential", "base": 2, "cap": 15}
    )

    assert isinstance(config.root, GenericBackoffConfig)
    assert config.root.strategy == "exponential"
    assert config.root.base == 2
    assert config.root.cap == 15


def test_redis_config_default_backoff() -> None:
    config = RedisConfig.model_validate({"url": "redis://localhost:6379/0"})

    assert config.backoff is not None
    assert isinstance(config.backoff.root, GenericBackoffConfig)
    assert config.backoff.root.strategy == "decorrelated_jitter"
