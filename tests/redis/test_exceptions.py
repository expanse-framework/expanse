from __future__ import annotations

from expanse.redis.exceptions import MissingRedisPackageError
from expanse.redis.exceptions import UnconfiguredConnectionError


def test_unconfigured_connection_error_is_an_exception() -> None:
    error = UnconfiguredConnectionError("test")

    assert isinstance(error, Exception)
    assert str(error) == "test"


def test_missing_redis_package_error_is_an_exception() -> None:
    error = MissingRedisPackageError("test")

    assert isinstance(error, Exception)
    assert str(error) == "test"
